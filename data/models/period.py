from uuid import uuid4

from pydantic import BaseModel


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
