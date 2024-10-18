from typing import Optional

from pydantic import BaseModel, ConfigDict

from application.logs import log_exceptions
from lib.errors import CommunicationError
from lib.funcs import fetch_json


class SensorNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    adjustment: Optional[float] = None

    @log_exceptions("models.SensorNode")
    async def temperature(self) -> Optional[float]:
        res = await fetch_json(self.url)

        if res is None:
            raise CommunicationError(f"Failed to get temperature from URL: {self.url}")

        temp = float(res["temperature"])

        if self.adjustment is not None:
            temp += self.adjustment

        return float(f"{temp:.1f}")
