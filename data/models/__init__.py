import time
from typing import Optional
from uuid import uuid4

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


class SensorNode(BaseModel):
    url: str
    adjustment: Optional[float] = None
    cached_value: Optional[float] = None
    last_updated: float = 0
    expiry_time: int = 60

    @log_exceptions("models.SensorNode")
    def temperature(self):
        if self.cached_value and self.last_updated + self.expiry_time > time.time():
            return self.cached_value

        res = requests.get(self.url, timeout=5).json()
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

    @log_exceptions("models.RelayNode")
    def switch(self, direction="on"):
        if direction == "on":
            requests.get(f"{self.url_on}", timeout=5)
        elif direction == "off":
            requests.get(f"{self.url_off}", timeout=5)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions("models.RelayNode")
    def status(self) -> bool:
        if (
            self.cached_value is not None
            and self.last_updated + self.expiry_time > time.time()
        ):
            return self.cached_value

        resp = requests.get(f"{self.url_status}", timeout=5)

        self.cached_value = not int(resp.content)
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
