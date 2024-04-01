from typing import Optional

import time
from pydantic import BaseModel

from application.logs import log_exceptions
from lib.funcs import fetch_json


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
