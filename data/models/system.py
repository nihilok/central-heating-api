import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union, Optional, AsyncIterable, Callable
import time

import aiofiles
from pydantic import BaseModel

from application.constants import DEFAULT_MINIMUM_TARGET
from application.logs import get_logger, log_exceptions
from data.models import SensorNode, RelayNode, Period

DEFAULT_ROOM_TEMP = 22
PERSISTENCE_FILE = (
    Path(os.path.dirname(os.path.abspath(__file__))).parent / "persistence.json"
)
logger = get_logger()
file_semaphore = asyncio.Semaphore(1)


class CachedProperty:
    def __init__(self, func, expiry_seconds):
        self.func = func
        self.expiry_seconds = expiry_seconds
        self.value = None
        self.last_updated = None

    def __repr__(self):
        return str(self.value)

    def __get__(self, instance, owner):
        print("\n\n\n\n")
        print(self.value)
        if (
            self.last_updated is None
            or time.time() - self.last_updated > self.expiry_seconds
        ):
            self.value = self.func(instance)
            print("\n\n\n\n")
            print(self.value)
            self.last_updated = time.time()
        return self.value

    # Implementing the less than comparison
    def __lt__(self, other):
        if self.value is None:
            return False
        return self.value < other

    def __ge__(self, other):
        if (
            self.value is None
            and other is not None
            or self.value is not None
            and other is None
        ):
            return False
        if self.value == other:
            return True

        return self.value > other

    def __eq__(self, other):
        if self.value is None and other is not None:
            return False
        return self.value == other


def cached_property_expiry(expiry_seconds) -> Callable:
    def decorator(func):
        return CachedProperty(func, expiry_seconds)

    return decorator


class System(BaseModel):
    sensor: SensorNode
    relay: RelayNode
    system_id: Union[int, str]
    program: bool = False
    periods: list[Period] = []
    advance: Optional[float] = None
    boost: Optional[float] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._temperature = None
        self._temperature_expiry = None
        self._expiry_seconds = 120

    async def temperature(self):
        if self._temperature_expiry is not None and self._temperature_expiry > time.time():
            self._temperature = None
        if self._temperature is None:
            return await self.sensor.temperature()
        return self._temperature

    async def set_temperature(self, temperature: float):
        self._temperature = temperature
        self._temperature_expiry = time.time() + self._expiry_seconds

    async def relay_on(self):
        return await self.relay.status()

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

    def sorted_periods(self) -> list:
        return sorted(self.periods, key=lambda p: f"{p.start}-{p.end}")

    @property
    def next_target(self):
        check_time = self._decimal_time()
        check_day = self._the_day_today()

        try:
            period = next(
                filter(
                    lambda p: p.end > check_time and p.days.dict()[check_day],
                    self.sorted_periods(),
                )
            )
        except StopIteration:
            check_day = self._the_day_today(plus_days=1)
            try:
                return next(
                    filter(
                        lambda p: p.days.dict()[check_day],
                        self.sorted_periods(),
                    )
                ).target
            except StopIteration:
                return DEFAULT_ROOM_TEMP
        return period.target

    @log_exceptions("system")
    def switch_on(self):
        self.relay.switch("on")

    @log_exceptions("system")
    def switch_off(self):
        self.relay.switch("off")

    @log_exceptions("system")
    async def async_switch_on(self):
        await self.relay.async_switch("on")

    @log_exceptions("system")
    async def async_switch_off(self):
        await self.relay.async_switch("off")

    @log_exceptions("system")
    def add_period(self, period: Period):
        update = None
        if period in self.periods:
            return

        for period_ in self.periods:
            # Same period
            if period_.start == period_.start and period_.end == period_.end:
                update = period_
                break

            # Overlapping period
            elif (period_.start < period_.end) and (period_.end > period_.start):
                return
        if update:
            new_periods = [p for p in self.periods if p.id != update.id]
        else:
            new_periods = self.periods.copy()
        new_periods.append(period)
        new_periods.sort(key=lambda p: f"{p.start}-{p.end}")
        self.periods = new_periods

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

    @log_exceptions("system")
    async def serialize(self):
        logger.debug(f"Acquiring semaphore {self.system_id}")
        async with file_semaphore:
            logger.debug(f"Writing to file {self.system_id}")
            sensor_dict = self.sensor.model_dump(exclude_unset=True)
            relay_dict = self.relay.model_dump(exclude_unset=True)
            serialised_data = {
                "relay": relay_dict,
                "sensor": sensor_dict,
                "system_id": self.system_id,
                "program": self.program,
                "periods": [p.model_dump() for p in self.periods],
                "advance": self.advance,
                "boost": self.boost,
                "temperature": self._temperature,
                "temperature_expiry": self._temperature_expiry
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
                temperature = system.get("temperature")
                expiry = system.get("expiry")
                system = System(
                    relay=relay,
                    sensor=sensor,
                    system_id=system["system_id"],
                    program=system["program"],
                    periods=[Period(**p) for p in system["periods"]],
                    advance=advance,
                    boost=boost,
                )
                system._temperature = temperature
                system._temperature_expiry = expiry
                yield system
            except Exception as e:
                logger.error(e)
                continue

    @classmethod
    @log_exceptions("system")
    async def get_by_id(cls, system_id):
        async for system in cls.deserialize_systems():
            if system and system.system_id == system_id:
                return system
