import time

from application.event_loop_manager import EventLoopManager
from data.models.system import System
from application.logs import get_logger, log_exceptions

from application.constants import THERMOSTAT_THRESHOLD

BOOST_THRESHOLD = 26

logger = get_logger(__name__)


class CommunicationError(Exception):
    pass


@log_exceptions("event_loop")
async def run_check(system: System) -> bool:
    should_switch_on = False
    logger.debug(f"Running temperature check ({system.system_id})")
    temperature, target = await system.temperature(), system.current_target
    logger.debug(f"{temperature=} {target=}")

    if temperature is None:
        # system failed to communicate with temperature node.
        raise CommunicationError(
            f"Temperature reading for system '{system.system_id}' is not available"
        )

    relay_state = await system.relay_on()

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

    if system.boost and system.boost > current_time and temperature < BOOST_THRESHOLD:
        logger.debug("BOOST ON!")
        should_switch_on = True
        return should_switch_on
    elif system.boost and system.boost <= current_time:
        system.boost = None

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


async def heating_task():
    async for system in System.deserialize_systems():
        if not system:
            continue
        try:
            if await run_check(system) is True:
                await system.async_switch_on()
            else:
                await system.async_switch_off()
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")
            await system.async_switch_off()


@log_exceptions("event_loop")
async def graceful_shutdown():
    async for system in System.deserialize_systems():
        if system:
            logger.debug(f"Switching off {system.system_id} relay")
            await system.async_switch_off()


event_loop = EventLoopManager(heating_task, graceful_shutdown)
