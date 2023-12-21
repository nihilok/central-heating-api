import asyncio
import functools
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union, Optional, Iterable, AsyncIterable
from uuid import uuid4

import aiofiles
import requests
from pydantic import BaseModel, ValidationError

from application.constants import DEFAULT_MINIMUM_TARGET
from application.logs import log_exceptions, get_logger

DEFAULT_ROOM_TEMP = 22

PERSISTENCE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "persistence.json"
file_lock = False

logger = get_logger()

"""
// EXAMPLE:
{
  "systems": [
    {
      "system_id": "downstairs",
      "relay": {
        "url_on":  "http://192.168.1.115/off?pin=1",
        "url_off":  "http://192.168.1.115/on?pin=1",
        "url_status":  "http://192.168.1.115/status?pin=1"
      },
      "sensor": {
        "url": "http://192.168.1.116"
      },
      "program": true,
      "periods": "[[6.0, 22.0, 22.0]]"
    },
    {
      "system_id": "upstairs",
      "relay": {
        "url_on":  "http://192.168.1.115/off?pin=2",
        "url_off":  "http://192.168.1.115/on?pin=2",
        "url_status":  "http://192.168.1.115/status?pin=2"
      },
      "sensor": {
        "url": "http://192.168.1.109"
      },
      "program": true,
      "periods": "[[3.0, 10.0, 22.0], [18.0, 23.0, 22.0]]"
    }
  ]
}
"""


class SensorNode(BaseModel):
    url: str
    adjustment: Optional[float] = None

    @log_exceptions
    def temperature(self):
        res = requests.get(self.url, timeout=5).json()
        temp = float(res["temperature"])
        if self.adjustment is not None:
            temp += self.adjustment
        return float(f"{temp:.1f}")


class RelayNode(BaseModel):
    url_on: str
    url_off: str
    url_status: str

    @log_exceptions
    def switch(self, direction="on"):
        if direction == "on":
            requests.get(f"{self.url_on}", timeout=5)
        elif direction == "off":
            requests.get(f"{self.url_off}", timeout=5)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions
    def status(self):
        resp = requests.get(f"{self.url_status}", timeout=5)
        return not int(resp.content)


class Days(BaseModel):
    monday: bool = True
    tuesday: bool = True
    wednesday: bool = True
    thursday: bool = True
    friday: bool = True
    saturday: bool = True
    sunday: bool = True


default_days = Days()


class Period(BaseModel):
    start: float
    end: float
    target: float
    days: Days = default_days
    id: str = uuid4().hex


file_semaphore = asyncio.Semaphore(1)


class System(BaseModel):
    sensor: SensorNode
    relay: RelayNode
    system_id: Union[int, str]
    program: bool = False
    periods: list[Period] = []
    advance: Optional[float] = None
    boost: Optional[float] = None

    @property
    def temperature(self):
        return self.sensor.temperature()

    @property
    def relay_on(self):
        return self.relay.status()

    @staticmethod
    def _decimal_time():
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute_decimal = current_time.minute / 60
        check_time = current_hour + current_minute_decimal
        return check_time

    @staticmethod
    def _the_day_today(plus_days=0):
        t = datetime.now() + timedelta(days=plus_days)
        return t.strftime("%A").lower()

    @property
    def current_target(self):
        if self.boost:
            return 999
        if self.advance:
            return self.next_target

        if not self.program:
            return DEFAULT_MINIMUM_TARGET

        check_time = self._decimal_time()
        check_day = self._the_day_today()
        try:
            period = next(
                filter(
                    lambda x: x.start <= check_time < x.end
                    and x.days.dict()[check_day],
                    self.periods,
                )
            )
        except StopIteration:
            return DEFAULT_MINIMUM_TARGET
        return period.target

    @property
    def next_target(self):
        check_time = self._decimal_time()
        check_day = self._the_day_today(plus_days=1)

        try:
            period = next(
                filter(
                    lambda x: x.end > check_time and x.days.dict()[check_day],
                    sorted(self.periods, key=lambda p: p.end),
                )
            )
        except StopIteration:
            try:
                return next(
                    filter(
                        lambda d: d.days.dict()[check_day],
                        sorted(self.periods, key=lambda p: p.start),
                    )
                ).target
            except StopIteration:
                return DEFAULT_ROOM_TEMP
        return period.target

    @log_exceptions
    def switch_on(self):
        self.relay.switch("on")

    @log_exceptions
    def switch_off(self):
        self.relay.switch("off")

    @log_exceptions
    def add_period(self, period: Period):
        update = None
        if period in self.periods:
            return

        for p in self.periods:
            # Same period
            if p.start == period.start or p.end == period.end:
                update = p
                break

            # Overlapping period
            elif (p.start < period.end) and (p.end > period.start):
                return
        if update:
            self.periods = list(
                filter(
                    lambda x: x.id != update.id,
                    self.periods,
                )
            )

        self.periods.append(period)
        self.periods.sort(key=lambda x: x.start)
        self.serialize()

    def check_periods(self, periods_in):
        if (add_remove := len(periods_in) - len(self.periods)) == 0:
            return
        p1 = set(self.periods)
        p2 = set(periods_in)
        if add_remove > 0:
            self.periods.extend(p1.difference(p2))
        else:
            self.periods = periods_in

    async def attribute_changed(self):
        await self.serialize()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key not in {"periods", "advance", "boost", "program"}:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.attribute_changed())
        except RuntimeError:
            pass

    @log_exceptions
    async def serialize(self):
        logger.debug(f"Acquiring semaphore {self.system_id}")
        async with file_semaphore:
            logger.debug(f"Writing to file {self.system_id}")
            sensor_dict = self.sensor.dict(exclude_unset=True)
            relay_dict = self.relay.dict(exclude_unset=True)
            serialised_data = {
                "relay": relay_dict,
                "sensor": sensor_dict,
                "system_id": self.system_id,
                "program": self.program,
                "periods": [p.dict() for p in self.periods],
                "advance": self.advance,
                "boost": self.boost,
            }

            try:
                async with aiofiles.open(PERSISTENCE_FILE, mode="r") as f:
                    content = await f.read()
                    current = json.loads(content)
            except FileNotFoundError:
                current = {"systems": []}

            updated_systems = list(
                filter(lambda x: x["system_id"] != self.system_id, current["systems"])
            )

            updated_systems.append(serialised_data)

            current["systems"] = updated_systems

            async with aiofiles.open(PERSISTENCE_FILE, "w") as f:
                await f.write(json.dumps(current, indent=2))
            logger.debug(f"Releasing semaphore {self.system_id}")

    @classmethod
    async def deserialize_systems(cls) -> AsyncIterable["System"]:
        try:
            async with aiofiles.open(PERSISTENCE_FILE, "r") as f:
                content = await f.read()
                current = json.loads(content)
        except FileNotFoundError:
            raise StopAsyncIteration
        for system in current["systems"]:
            try:
                relay = RelayNode(**system["relay"])
                sensor = SensorNode(**system["sensor"])
                advance = system.get("advance")
                boost = system.get("boost")
                system = System(
                    relay=relay,
                    sensor=sensor,
                    system_id=system["system_id"],
                    program=system["program"],
                    periods=[Period(**p) for p in system["periods"]],
                    advance=advance,
                    boost=boost,
                )
                yield system
            except Exception as e:
                logger.error(e)
                continue

    @classmethod
    @log_exceptions
    async def get_by_id(cls, system_id):
        async for system in cls.deserialize_systems():
            if system and system.system_id == system_id:
                return system
