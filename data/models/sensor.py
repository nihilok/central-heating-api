from typing import Optional

import time
from pydantic import BaseModel

from application.logs import log_exceptions
from lib.funcs import fetch_json


class SensorNode(BaseModel):
    url: str
    adjustment: Optional[float] = None

    @log_exceptions("models.SensorNode")
    async def temperature(self) -> float:
        res = await fetch_json(self.url)

        temp = float(res["temperature"])
        if self.adjustment is not None:
            temp += self.adjustment

        return float(f"{temp:.1f}")
