import os

from typing import Optional, Union

from pydantic import ValidationError

from application.constants import DEFAULT_MINIMUM_TARGET, CHECK_FREQUENCY_SECONDS
from application.models import SystemUpdate, PeriodsBody, SystemOut, AdvanceBody
from application.logs import get_logger
from data.models.system import System
from fastapi import APIRouter, HTTPException, Depends

from application.event_loop import event_loop as heating_event_loop
from authentication import get_current_user

router = APIRouter(prefix="/api/v3")
logger = get_logger(__name__)


async def get_system_by_id_or_404(system_id) -> System:
    system = await System.get_by_id(system_id)
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
        async for s in systems
        if s is not None
    ]


@router.get("/systems/{system_id}/}")
async def get_system(system_id: Optional[str] = None) -> SystemOut:
    system = await get_system_by_id_or_404(system_id)
    return SystemOut(
        **system.dict()
        | {"is_within_period": system.current_target > DEFAULT_MINIMUM_TARGET}
    )


@router.post("/systems/", dependencies=[Depends(get_current_user)])
async def new_or_update_system(system_update: SystemUpdate):
    system = await get_system_by_id_or_404(system_update.system_id)
    try:
        System(
            system_id=system_update.system_id,
            relay=system_update.relay or system.relay,
            sensor=system_update.sensor or system.sensor,
            periods=system_update.periods or system.periods,
            program=system_update.program
            if system_update.program is not None
            else system.program,
        )
        return {}
    except ValidationError as ve:
        raise HTTPException(422, "Unprocessable Entity") from ve
    except Exception as e:
        raise HTTPException(400, "Bad Request") from e


@router.get("/temperature/{system_id}/")
async def temperature(system_id: Union[int, str]):
    system = await get_system_by_id_or_404(system_id)
    return {"temperature": await system.temperature()}


@router.get("/target/{system_id}/")
async def target(system_id: Union[int, str]):
    system = await get_system_by_id_or_404(system_id)
    return {
        "current_target": system.current_target,
        "relay_on": await system.relay_on(),
    }


@router.post("/periods/{system_id}/", dependencies=[Depends(get_current_user)])
async def periods(system_id: Union[int, str], body: PeriodsBody):
    system = await get_system_by_id_or_404(system_id)
    system.periods = body.periods
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/advance/{system_id}/", dependencies=[Depends(get_current_user)])
async def advance(system_id: Union[int, str], body: AdvanceBody):
    system = await get_system_by_id_or_404(system_id)
    system.advance = body.end_time
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/boost/{system_id}/", dependencies=[Depends(get_current_user)])
async def boost(system_id: Union[int, str], body: AdvanceBody):
    system = await get_system_by_id_or_404(system_id)
    system.boost = body.end_time
    return SystemOut(**system.dict(exclude_unset=True))


@router.post("/cancel_all/{system_id}/")
async def cancel(system_id: Union[int, str]):
    system = await get_system_by_id_or_404(system_id)
    if system.boost:
        system.boost = None
    if system.advance:
        system.advance = None
    return SystemOut(**system.dict(exclude_unset=True))


@router.get("/all_data/")
async def get_all_data():
    systems = System.deserialize_systems()
    data = []
    async for system in systems:
        data.append(
            {
                "id": system.system_id,
                "temperature": await system.temperature(),
                "target": system.current_target,
                "relay_on": await system.relay_on(),
            }
        )
    return {"systems": sorted(data, key=lambda x: x["id"], reverse=True)}


@router.post("/program/{system_id}/{on}/", dependencies=[Depends(get_current_user)])
async def program(system_id: str, on: str):
    system = await get_system_by_id_or_404(system_id)
    if on not in {"on", "off"}:
        raise HTTPException(404, "NOT FOUND")
    system.program = True if on == "on" else False
    return {"program_on": system.program}


@router.get("/start_loop/", dependencies=[Depends(get_current_user)])
async def start():
    heating_event_loop.run(CHECK_FREQUENCY_SECONDS)
    return {"detail": "all systems go!"}


@router.get("/stop_loop/", dependencies=[Depends(get_current_user)])
async def stop():
    await heating_event_loop.stop_and_cleanup()
    return {"detail": "stopped"}


@router.post("/reboot_system/", dependencies=[Depends(get_current_user)])
async def reboot():
    os.system("sudo reboot")
    return {}


@router.post("/receive/{sensor_id}/")
async def receive(sensor_id: str, data: dict):
    system = await get_system_by_id_or_404(sensor_id)
    t = data.get("temperature")
    if t is None:
        return {}
    if isinstance(t, str):
        t = float(t)
    await system.set_temperature(t)
    return {}
