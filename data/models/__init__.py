import time
from typing import Optional
from uuid import uuid4

import aiohttp
import requests
from pydantic import BaseModel

from application.logs import log_exceptions

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


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.ok:
                return await response.json()


async def fetch_text(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.ok:
                return await response.text()


class SensorNode(BaseModel):
    url: str
    adjustment: Optional[float] = None
    cached_value: Optional[float] = None
    last_updated: float = 0
    expiry_time: int = 60

    @log_exceptions("models.SensorNode")
    async def temperature(self):
        if self.cached_value and self.last_updated + self.expiry_time > time.time():
            return self.cached_value

        res = await fetch_json(self.url)
        if res is None:
            return self.cached_value

        temp = float(res["temperature"])
        if self.adjustment is not None:
            temp += self.adjustment

        self.cached_value = float(f"{temp:.1f}")
        self.last_updated = time.time()
        return self.cached_value


class RelayNode(BaseModel):
    url_on: str
    url_off: str
    url_status: str
    cached_value: Optional[bool] = None
    last_updated: float = 0
    expiry_time: int = 10
    URLS: Optional[dict] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.URLS = {"on": f"{self.url_on}", "off": f"{self.url_off}"}

    @log_exceptions("models.RelayNode")
    def switch(self, direction="on"):
        try:
            url = self.URLS[direction]
            requests.get(f"{url}", timeout=5)
        except KeyError:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions("models.RelayNode")
    async def async_switch(self, direction="off"):
        try:
            url = self.URLS[direction]
            return await self.hit_switch(url)
        except KeyError:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions("models.RelayNode")
    async def status(self) -> Optional[bool]:
        if (
            self.cached_value is not None
            and self.last_updated + self.expiry_time > time.time()
        ):
            return self.cached_value

        resp = await fetch_text(f"{self.url_status}")
        if resp is None:
            return self.cached_value

        self.cached_value = not int(resp)
        self.last_updated = time.time()
        return self.cached_value


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
