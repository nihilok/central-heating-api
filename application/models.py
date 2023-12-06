from datetime import datetime
from typing import Union, Optional

from pydantic import BaseModel

from data.models import RelayNode, SensorNode, Period


class SystemUpdate(BaseModel):
    system_id: Union[int, str]
    relay: Optional[RelayNode] = None
    sensor: Optional[SensorNode] = None
    periods: Optional[list[Period]] = None
    program: Optional[bool] = None


class PeriodsBody(BaseModel):
    periods: list[Period]


class AdvanceBody(BaseModel):
    end_time: float


class SystemOut(BaseModel):
    system_id: str
    periods: list[Period]
    program: bool
    advance: Optional[datetime] = None
    boost: Optional[datetime] = None
    is_within_period: bool
