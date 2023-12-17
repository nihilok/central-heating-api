import os

from typing import Optional, Union

from pydantic import ValidationError

from application.constants import DEFAULT_MINIMUM_TARGET
from application.models import SystemUpdate, PeriodsBody, SystemOut, AdvanceBody
from application.logs import get_logger
from data.models import System
from fastapi import APIRouter, HTTPException, Depends

from application.event_loop import (
    run_async_loop,
    stop_async_loop,
)
from authentication import get_current_user

router = APIRouter(prefix="/api/v3")
logger = get_logger(__name__)


def get_system_by_id_or_404(system_id) -> System:
    system = System.get_by_id(system_id)
    if not system:
        raise HTTPException(404, "System not found")
    return system


@router.get("/systems/")
async def get_systems() -> list[SystemOut]:
    systems = System.deserialize_systems()
    return [
        SystemOut(
            **s.dict(exclude_unset=True)
            | {"is_within_period": s.current_target > DEFAULT_MINIMUM_TARGET}
        )
        for s in systems
        if s is not None
    ]


@router.get("/systems/{system_id}/}")
async def get_system(system_id: Optional[str] = None) -> SystemOut:
    system = get_system_by_id_or_404(system_id)
    return SystemOut(
        **system.dict()
        | {"is_within_period": system.current_target > DEFAULT_MINIMUM_TARGET}
    )


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
    except ValidationError as ve:
        raise HTTPException(422, "Unprocessable Entity") from ve
    except Exception as e:
        raise HTTPException(400, "Bad Request") from e


@router.get("/temperature/{system_id}/")
async def temperature(system_id: Union[int, str]):
    system = get_system_by_id_or_404(system_id)
    return {"temperature": system.temperature}


@router.get("/target/{system_id}/")
async def target(system_id: Union[int, str]):
    system = get_system_by_id_or_404(system_id)
    return {
        "current_target": system.current_target,
        "relay_on": system.relay_on,
    }


@router.post("/periods/{system_id}/", dependencies=[Depends(get_current_user)])
async def periods(system_id: Union[int, str], body: PeriodsBody):
    system = get_system_by_id_or_404(system_id)
    system.periods = body.periods
    system.serialize()
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/advance/{system_id}/", dependencies=[Depends(get_current_user)])
async def advance(system_id: Union[int, str], body: AdvanceBody):
    system = get_system_by_id_or_404(system_id)
    system.advance = body.end_time
    system.serialize()
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/boost/{system_id}/", dependencies=[Depends(get_current_user)])
async def boost(system_id: Union[int, str], body: AdvanceBody):
    system = get_system_by_id_or_404(system_id)
    system.boost = body.end_time
    system.serialize()
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/cancel_all/{system_id}/")
async def cancel(system_id: Union[int, str]):
    system = get_system_by_id_or_404(system_id)
    system.boost = None
    system.advance = None
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


@router.post("/program/{system_id}/{on}/", dependencies=[Depends(get_current_user)])
async def program(system_id: str, on: str):
    system = get_system_by_id_or_404(system_id)
    if on not in {"on", "off"}:
        raise HTTPException(404, "NOT FOUND")
    system.program = True if on == "on" else False
    system.serialize()
    return {"program_on": system.program}


@router.get("/start_loop/", dependencies=[Depends(get_current_user)])
async def start():
    run_async_loop()
    return {"detail": "all systems go!"}


@router.get("/stop_loop/", dependencies=[Depends(get_current_user)])
async def stop():
    await stop_async_loop()
    return {"detail": "stopped"}


@router.post("/reboot_system/", dependencies=[Depends(get_current_user)])
async def reboot():
    os.system("sudo reboot")
    return {}
