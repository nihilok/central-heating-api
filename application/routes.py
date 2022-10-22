from typing import Optional, Union

from pydantic import BaseModel

from data.models import Period, RelayNode, SensorNode, System
from fastapi import APIRouter, HTTPException

from application.event_loop import (
    run_async_loop,
    stop_async_loop,
)

router = APIRouter(prefix="/api/v3")


@router.get("/systems/")
async def get_systems(system_id: Optional[str] = None):
    try:
        ss = System.deserialize_systems()
        if system_id is None:
            return [SystemOut(**s.dict(exclude_unset=True)) for s in ss]
        for system in ss:
            if system.system_id == system_id:
                return SystemOut(**system.dict())
    except FileNotFoundError:
        raise HTTPException(404, "No persistent system(s) found")


class SystemUpdate(BaseModel):
    system_id: Union[int, str]
    relay: Optional[RelayNode] = None
    sensor: Optional[SensorNode] = None
    periods: Optional[list[Period]] = None
    program: Optional[bool] = None


@router.post("/systems/")
async def new_or_update_system(system_update: SystemUpdate):
    system = System.get_by_id(system_update.system_id)
    if system is None:
        raise HTTPException(404, "NOT FOUND")
    try:
        new = System(
            system_id=system_update.system_id,
            relay=system_update.relay or system.relay,
            sensor=system_update.sensor or system.sensor,
            periods=system_update.periods or system.periods,
            program=system_update.program
            if system_update.program is not None
            else system.program,
        )
        new.serialize()
        return {}
    except:
        raise HTTPException(400, "Bad Request")


@router.get("/temperature/{system_id}/")
async def temperature(system_id: Union[int, str]):
    systems = System.deserialize_systems()
    try:
        system = list(filter(lambda x: x.system_id == system_id, systems))[0]
        return system.temperature
    except IndexError:
        raise HTTPException(404, "System not found")


@router.get("/target/{system_id}/")
async def target(system_id: Union[int, str]):
    systems = System.deserialize_systems()
    try:
        system = list(filter(lambda x: x.system_id == system_id, systems))[0]
        return {"current_target": system.current_target, "relay_on": system.relay_on}
    except IndexError:
        raise HTTPException(404, "System not found")
    except ValueError:
        raise HTTPException(404, "Status URL not found")


class PeriodsBody(BaseModel):
    periods: list[list[float]]


class SystemOut(BaseModel):
    system_id: str
    periods: list[list[float]]
    program: bool


def get_system_by_id(system_id):
    systems = System.deserialize_systems()
    try:
        system = list(filter(lambda x: x.system_id == system_id, systems))[0]
    except IndexError:
        raise ValueError("System id not matched")
    return system


@router.post("/periods/{system_id}/")
async def target(system_id: Union[int, str], body: PeriodsBody):
    try:
        system = get_system_by_id(system_id)
        for p in body.periods:
          period = Period(start=p[0], end=p[1], target=p[2])
          system.add_period(period)
        system.serialize()
        system = get_system_by_id(system_id)
        return SystemOut(**system.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/start_loop/")
async def start():
    run_async_loop()
    return {"detail": "all systems go!"}


@router.get("/stop_loop/")
async def stop():
    await stop_async_loop()
    return {"detail": "stopped"}
