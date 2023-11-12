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
    systems = System.deserialize_systems()
    if system_id is None:
        return [SystemOut(**s.dict(exclude_unset=True)) for s in systems]
    for system in systems:
        if system.system_id == system_id:
            return SystemOut(**system.dict())


def get_system_by_id_or_404(system_id):
    system = System.get_by_id(system_id)
    if not system:
        raise HTTPException(404, "System not found")


@router.post("/systems/", dependencies=[Depends(get_current_user)])
async def new_or_update_system(system_update: SystemUpdate):
    system = get_system_by_id_or_404(system_update.system_id)
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
    system = get_system_by_id_or_404(system_update.system_id)
    return {"temperature": system.temperature}



@router.get("/target/{system_id}/")
async def target(system_id: Union[int, str]):
    system = get_system_by_id_or_404(system_update.system_id)
    return {
        "current_target": system.current_target
        if not system.advance
        else system.next_target,
        "relay_on": system.relay_on,
    }


@router.post("/periods/{system_id}/", dependencies=[Depends(get_current_user)])
async def target(system_id: Union[int, str], body: PeriodsBody):
    system = get_system_by_id_or_404(system_update.system_id)
    p_in = [Period(*p) for p in body.periods]
    if len(p_in) < len(system.periods):
        system.periods = []
    for p in p_in:
        system.add_period(p)
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/advance/{system_id}/", dependencies=[Depends(get_current_user)])
async def target(system_id: Union[int, str], body: AdvanceBody):
    system = get_system_by_id_or_404(system_update.system_id)
    system.advance = body.end_time
    system.serialize()
    return SystemOut(**system.dict(exclude_unset=True))



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
