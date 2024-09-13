import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Union, Optional, AsyncIterable

import aiofiles
from pydantic import BaseModel

from application.constants import DEFAULT_MINIMUM_TARGET
from application.logs import get_logger, log_exceptions
from data.models.period import Period
from data.models.relay import RelayNode
from data.models.sensor import SensorNode

DEFAULT_ROOM_TEMP = 22
PERSISTENCE_FILE = (
    Path(os.path.dirname(os.path.abspath(__file__))).parent / "persistence.json"
)
logger = get_logger(__name__)
file_semaphore = asyncio.Semaphore(1)


class System(BaseModel):
    sensor: SensorNode
    relay: RelayNode
    system_id: Union[int, str]
    program: bool = False
    periods: list[Period] = []
    advance: Optional[float] = None
    boost: Optional[float] = None
    disabled: bool = False
    error_count: int = 0
    max_error_count: int = 5
    temperature_expiry: Optional[float] = None
    expiry_seconds: int = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._temperature = None
        self._initialized = True
        self._updating = False

    async def temperature(self):
        if self.temperature_expiry is None or self.temperature_expiry <= time.time():
            logger.debug(f"Clearing cached temperature for {self.system_id}")
            self._temperature = None
        if self._temperature is None:
            logger.debug(f"Getting temperature for {self.system_id} from sensor")
            self._temperature, last_updated = await self.sensor.temperature()
            if self._temperature is None:
                self.error_count += 1
                if self.error_count >= self.max_error_count:
                    logger.warning(
                        f"Disabling system {self.system_id} after {self.error_count} errors getting temperature"
                    )
                    self.disabled = True
            if last_updated:
                self.temperature_expiry = last_updated + self.expiry_seconds

        return self._temperature

    async def set_temperature(self, temperature: float):
        adjustment = self.sensor.adjustment or 0
        actual = temperature + adjustment
        self._temperature = float(f"{actual:.1f}")
        self.temperature_expiry = time.time() + self.expiry_seconds

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
        logger.debug(f"Getting current target for {self.system_id}")
        if self.boost:
            logger.debug(f"Boost enabled for {self.system_id}")
            return 999
        if self.advance:
            logger.debug(f"Advance enabled for {self.system_id}")
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
        logger.debug(f"Getting next target for {self.system_id}")
        check_time = self._decimal_time()
        check_day = self._the_day_today()

        period = next(
            filter(
                lambda p: p.end > check_time and p.days.dict()[check_day],
                self.sorted_periods(),
            ),
            None,
        )

        if period is None:
            check_day = self._the_day_today(plus_days=1)

            period = next(
                filter(
                    lambda p: p.days.dict()[check_day],
                    self.sorted_periods(),
                )
            )
            if period is None:
                return DEFAULT_ROOM_TEMP

        return period.target

    async def switch_on(self):
        await self.relay.switch("on")

    async def switch_off(self):
        await self.relay.switch("off")

    async def attribute_changed(self):
        await self.serialize()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if not getattr(self, "_initialized", False):
            return
        if key in {
            "periods",
            "advance",
            "boost",
            "program",
            "_temperature",
            "error_count",
            "disabled",
        }:
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
                "temperature_expiry": self.temperature_expiry,
                "disabled": self.disabled,
                "error_count": self.error_count,
                "expiry_seconds": self.expiry_seconds,
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
        async with file_semaphore:
            try:
                async with aiofiles.open(PERSISTENCE_FILE, "r") as f:
                    content = await f.read()
                    conf = json.loads(content)
            except FileNotFoundError as e:
                raise StopAsyncIteration from e
            except JSONDecodeError as e:
                logger.error(content)
                logger.error(e)
                raise StopAsyncIteration from e
        for system in conf["systems"]:
            if system.get("disabled", False):
                logger.debug(f"System: {system['system_id']} is disabled")
                continue
            try:
                relay = RelayNode(**system["relay"])
                sensor = SensorNode(**system["sensor"])
                system_obj = cls(
                    relay=relay,
                    sensor=sensor,
                    system_id=system["system_id"],
                    program=system["program"],
                    periods=[Period(**p) for p in system["periods"]],
                    advance=system.get("advance"),
                    boost=system.get("boost"),
                    error_count=system["error_count"],
                    expiry_seconds=system.get("expiry_seconds", 20),
                )

                temperature_expiry = system.get("expiry_seconds", 20)
                temperature = system.get("temperature")
                if temperature and temperature_expiry:
                    system_obj._temperature = temperature
                    system_obj.temperature_expiry = temperature_expiry

                yield system_obj

            except Exception as e:
                logger.error(e)
                continue

    @classmethod
    @log_exceptions("system")
    async def get_by_id(cls, system_id):
        async for system in cls.deserialize_systems():
            if system and system.system_id == system_id:
                return system
