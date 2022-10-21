import asyncio
from typing import Callable

from data.models import System
from application.logs import get_logger, log_exceptions

from application.constants import (
    CHECK_FREQUENCY_SECONDS,
    THERMOSTAT_THRESHOLD,
)

GLOBAL_RUN_CONDITION_FLAG = True
logger = get_logger(__name__)


@log_exceptions
async def run_check(system: System):
    logger.debug(f"Running temperature check ({system.system_id})")
    temperature, target = system.temperature, system.current_target
    logger.debug(f"{temperature=} {target=}")
    if (
        system.program is True
        and temperature is not None
        and temperature < target - THERMOSTAT_THRESHOLD
    ):
        return True


async def event_loop(
    run_condition: Callable[[], bool],
    interval=CHECK_FREQUENCY_SECONDS,
):
    while run_condition():
        try:
            for system in System.deserialize_systems():
                if await run_check(system) is True:
                    system.switch_on()
                else:
                    system.switch_off()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")
            continue


@log_exceptions
async def graceful_shutdown():
    for system in System.deserialize_systems():
        logger.debug(f"Switching off {system.system_id} relay")
        system.switch_off()


@log_exceptions
def run_async_loop(interval_seconds: int = CHECK_FREQUENCY_SECONDS):
    global GLOBAL_RUN_CONDITION_FLAG
    GLOBAL_RUN_CONDITION_FLAG = True
    loop = asyncio.get_running_loop()
    loop.create_task(
        event_loop(
            run_condition=lambda: GLOBAL_RUN_CONDITION_FLAG,
            interval=interval_seconds,
        )
    )
    logger.info("Loop task created")


async def stop_async_loop():
    global GLOBAL_RUN_CONDITION_FLAG
    GLOBAL_RUN_CONDITION_FLAG = False
    await graceful_shutdown()
    logger.info("Loop task stopped")
