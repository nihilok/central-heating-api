import time

from application.event_loop_manager import EventLoopManager
from data.models.system import System
from application.logs import get_logger, log_exceptions

from application.constants import THERMOSTAT_THRESHOLD
from lib.errors import CommunicationError

BOOST_THRESHOLD = 26

logger = get_logger(__name__)


async def run_check(system: System) -> bool:
    should_switch_on = False
    temperature, target = system.temperature, system.current_target
    logger.debug(f"Running check for {system.system_id=} with {temperature=} {target=}")

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
            result = await run_check(system)
        except Exception as e:
            logger.error(e, exc_info=True)
            result = False

        if result is True:
            await system.switch_on()
        else:
            await system.switch_off()


@log_exceptions("event_loop.graceful_shutdown")
async def graceful_shutdown():
    logger.info("Gracefully shutting down all systems...")
    async for system in System.deserialize_systems():
        if system:
            logger.debug(f"Switching off {system.system_id} relay")
            await system.switch_off()


event_loop = EventLoopManager(heating_task, graceful_shutdown)
