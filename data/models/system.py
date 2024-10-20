import asyncio
import json
import yaml
import os
import time
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Union, Optional, AsyncIterable, Any

import aiofiles
from pydantic import BaseModel, ValidationError, ConfigDict

from application.constants import DEFAULT_MINIMUM_TARGET
from application.logs import get_logger, log_exceptions
from data.models.period import Period
from data.models.relay import RelayNode
from data.models.sensor import SensorNode
from lib.errors import CommunicationError

DEFAULT_ROOM_TEMP = 22
PERSISTENCE_FILE = (
    Path(os.path.dirname(os.path.abspath(__file__))).parent / "persistence.json"
)
CONFIG_FILE = Path(os.path.dirname(os.path.abspath(__file__))).parent / "config.yml"

logger = get_logger(__name__)
file_semaphore = asyncio.Semaphore(1)


class SystemConfig(BaseModel):
    systems: list["System"] = []

    @classmethod
    async def load_config(cls):
        async with aiofiles.open(PERSISTENCE_FILE, mode="r") as f:
            conf = json.loads(await f.read())
            return cls(systems=conf["systems"])


class System(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sensor: SensorNode
    relay: RelayNode
    system_id: Union[int, str]
    program: bool = False
    periods: list[Period] = []
    advance: Optional[float] = None
    boost: Optional[float] = None
    disabled: bool = False
    error_count: int = 0
    disabled_time: Optional[datetime] = None
    max_error_count: int = 5
    temperature_expiry: Optional[float] = None
    expiry_seconds: int = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._temperature = None
        self._initialized = False
        self._updating = False

    def model_dump(
        self,
        **kwargs,
    ) -> dict[str, Any]:
        dump = super().model_dump(**kwargs)
        dump["temperature"] = self._temperature
        return dump

    async def get_temperature(self):
        logger.debug(
            f"Getting temperature for {self.system_id} from sensor ({self.error_count + 1} of {self.max_error_count} retries)"
        )
        try:
            new_temperature = await self.sensor.temperature()
        except CommunicationError as e:
            self.error_count += 1
            if self.error_count >= self.max_error_count:
                logger.warning(
                    f"Disabling system {self.system_id} after {self.error_count} errors getting temperature"
                )
                self.disabled = True
                self.disabled_time = datetime.now()
                await self.attribute_changed()
                raise e
            await asyncio.sleep(5)
            return await self.get_temperature()
        self.error_count = 0
        return new_temperature

    async def temperature(self):
        if (
            self._temperature
            and self.temperature_expiry
            and self.temperature_expiry <= time.time()
        ):
            self._temperature = None

        if self._temperature is None:
            self._temperature = await self.get_temperature()

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
            try:
                current = await SystemConfig.load_config()
            except (FileNotFoundError, JSONDecodeError):
                current = SystemConfig()

            updated_systems = list(
                filter(lambda x: x.system_id != self.system_id, current.systems)
            )

            updated_systems.append(self)

            current.systems = [
                sys.model_dump(exclude_unset=True) for sys in updated_systems
            ]

            async with aiofiles.open(PERSISTENCE_FILE, "w") as f:
                await f.write(current.model_dump_json(indent=2))

            logger.debug(f"Releasing semaphore {self.system_id}")

    @classmethod
    async def deserialize_systems(cls) -> AsyncIterable["System"]:
        async with file_semaphore:
            conf = None
            try:
                async with aiofiles.open(PERSISTENCE_FILE, "r") as f:
                    content = await f.read()
                    conf = json.loads(content)
            except FileNotFoundError as e:
                pass
            except JSONDecodeError as e:
                logger.error(content)
                logger.error(e)
                pass

        if conf is None:
            with open(CONFIG_FILE, "r") as f:
                yml_string = f.read()
                logger.debug(yml_string)
                conf = yaml.safe_load(yml_string)
                logger.debug(conf)

            reserialise = True
        else:
            reserialise = False

        if conf is None:
            raise StopAsyncIteration

        for system in conf["systems"]:
            try:
                system_obj = cls(**system)

                if (
                    system_obj.disabled
                    and system_obj.disabled_time is not None
                    and system_obj.disabled_time + timedelta(minutes=15)
                    > datetime.now()
                ):
                    logger.warning(f"System {system_obj.system_id} is disabled")
                    continue
                elif system_obj.disabled:
                    system_obj.disabled = False
                    system_obj.disabled_time = None

                temperature = system.get("temperature")
                system_obj._temperature = temperature
                system_obj._initialized = True

                if reserialise:
                    await system_obj.serialize()

                yield system_obj

            except ValidationError as e:
                logger.error(e, exc_info=True)

    @classmethod
    @log_exceptions("system")
    async def get_by_id(cls, system_id):
        async for system in cls.deserialize_systems():
            if system and system.system_id == system_id:
                return system
