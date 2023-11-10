from typing import Optional, Union

from application.models import SystemUpdate, PeriodsBody, SystemOut, AdvanceBody
from application.logs import get_logger
from data.models import System, Period
from fastapi import APIRouter, HTTPException, Depends

from application.event_loop import (
    run_async_loop,
    stop_async_loop,
)
from authentication import get_current_user

router = APIRouter(prefix="/api/v3")
logger = get_logger(__name__)


@router.get("/systems/")
async def get_systems(system_id: Optional[str] = None):
    ss = System.deserialize_systems()
    if system_id is None:
        return [SystemOut(**s.dict(exclude_unset=True)) for s in ss]
    for system in ss:
        if system.system_id == system_id:
            return SystemOut(**system.dict())


@router.post("/systems/", dependencies=[Depends(get_current_user)])
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
        return {"temperature": system.temperature}
    except IndexError:
        raise HTTPException(404, "System not found")


@router.get("/target/{system_id}/")
async def target(system_id: Union[int, str]):
    systems = System.deserialize_systems()
    try:
        system = list(filter(lambda x: x.system_id == system_id, systems))[0]
        return {
            "current_target": system.current_target
            if not system.advance
            else system.next_target,
            "relay_on": system.relay_on,
        }
    except IndexError:
        raise HTTPException(404, "System not found")
    except ValueError:
        raise HTTPException(404, "Status URL not found")


def get_system_by_id(system_id):
    systems = System.deserialize_systems()
    try:
        system = list(filter(lambda x: x.system_id == system_id, systems))[0]
    except IndexError:
        raise ValueError("System id not matched")
    return system


@router.post("/periods/{system_id}/", dependencies=[Depends(get_current_user)])
async def target(system_id: Union[int, str], body: PeriodsBody):
    try:
        system = get_system_by_id(system_id)
        p_in = [Period(*p) for p in body.periods]
        if len(p_in) < len(system.periods):
            system.periods = []
        for p in p_in:
            system.add_period(p)
        return SystemOut(**system.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/advance/{system_id}/", dependencies=[Depends(get_current_user)])
async def target(system_id: Union[int, str], body: AdvanceBody):
    try:
        system = get_system_by_id(system_id)
        system.advance = body.end_time
        system.serialize()
        return SystemOut(**system.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/all_data/")
async def get_all_data():
    systems = System.deserialize_systems()
    data = []
    for system in sorted(systems, key=lambda x: x.system_id, reverse=True):
        data.append(
            {
                "id": system.system_id,
                "temperature": system.temperature,
                "target": system.current_target,
                "relay_on": system.relay_on,
            }
        )
    return {"systems": data}


@router.get("/start_loop/", dependencies=[Depends(get_current_user)])
async def start():
    run_async_loop()
    return {"detail": "all systems go!"}


@router.get("/stop_loop/", dependencies=[Depends(get_current_user)])
async def stop():
    await stop_async_loop()
    return {"detail": "stopped"}
