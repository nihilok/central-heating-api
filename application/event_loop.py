import asyncio
import time
from typing import Callable

from data.models import System
from application.logs import get_logger, log_exceptions

from application.constants import (
    CHECK_FREQUENCY_SECONDS,
    THERMOSTAT_THRESHOLD,
)

GLOBAL_RUN_CONDITION_FLAG = True
logger = get_logger(__name__)


class CommunicationError(Exception):
    pass


@log_exceptions
async def run_check(system: System) -> bool:
    should_switch_on = False
    logger.debug(f"Running temperature check ({system.system_id})")
    temperature, target = system.temperature, system.current_target
    logger.debug(f"{temperature=} {target=}")

    if temperature is None:
        # system failed to communicate with temperature node.
        raise CommunicationError(
            f"Temperature reading for system '{system.system_id}' is not available"
        )

    relay_state = system.relay_on

    if relay_state is None:
        # system failed to communicate with relay node.
        raise CommunicationError(
            f"Relay for system '{system.system_id}' is not available"
        )

    current_time = time.time()

    logger.debug(f"{current_time=} - {system.advance=} - {system.next_target=}")
    logger.debug(f"time: {system.advance and system.advance > current_time}")
    logger.debug(f"temp: {temperature < system.next_target}")

    if (
        system.advance
        and system.advance > current_time
        and temperature < system.current_target
    ):
        logger.debug("ADVANCE ON!")
        should_switch_on = True
        return should_switch_on
    elif system.advance and system.advance <= current_time:
        system.advance = None
        system.serialize()

    if system.boost and system.boost > current_time and temperature < 999:
        logger.debug("BOOST ON!")
        should_switch_on = True
        return should_switch_on
    elif system.boost and system.boost <= current_time:
        system.boost = None
        system.serialize()

    if not system.program:
        return should_switch_on

    if relay_state:
        if temperature >= target:
            return should_switch_on
        should_switch_on = True
        return should_switch_on
    else:
        if temperature <= target - THERMOSTAT_THRESHOLD:
            should_switch_on = True
            return should_switch_on
        return should_switch_on


@log_exceptions
async def loop_systems():
    for system in System.deserialize_systems():
        yield system


async def event_loop(
    run_condition: Callable[[], bool],
    interval=CHECK_FREQUENCY_SECONDS,
):
    while run_condition():
        async for system in loop_systems():
            try:
                if await run_check(system) is True:
                    system.switch_on()
                else:
                    system.switch_off()
            except Exception as e:
                logger.error(
                    f"ERROR in system '{system.system_id}': {e.__class__.__name__}: {e}"
                )

        await asyncio.sleep(interval)


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
