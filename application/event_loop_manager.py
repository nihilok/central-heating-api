import asyncio
import signal
from typing import Callable

from application.logs import get_logger

logger = get_logger("event_loop_manager")


class EventLoopManager:
    def __init__(
        self,
        event_loop_coroutine: Callable,
        cleanup_function: Callable,
        use_signals: bool = False,
        auto_restart: bool = True,
        max_retries: int = 3,
    ):
        self._event_loop_coroutine = event_loop_coroutine
        self._cleanup_function = cleanup_function
        self._should_run = True
        self._clean_up_triggered = False
        self._use_signals = use_signals
        self._auto_restart = auto_restart
        self.retries = 0
        self.max_retries = max_retries

    async def event_loop(self, interval: int):
        try:
            while self._should_run:
                await self._event_loop_coroutine()
                await asyncio.sleep(interval)
                self.retries = 0
        except Exception as e1:
            logger.error(e1, exc_info=True)
            try:
                await self._cleanup()
            except Exception as e2:
                logger.error(f"Cleanup on error failed: {e2}", exc_info=True)
            if not self._auto_restart or self.retries >= self.max_retries:
                raise e1
            self.retries += 1
            if self._should_run:
                logger.warning(
                    f"Attempting to restart task ({self.retries} of {self.max_retries} times)..."
                )
                return await self.event_loop(interval)

    def stop(self):
        self._should_run = False

    async def handle_signals(self):
        if not self._use_signals:
            return
        for sig_name in {"SIGINT", "SIGTERM"}:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(
                getattr(signal, sig_name),
                lambda: asyncio.create_task(self.stop_and_cleanup()),
            )

    async def _cleanup(self):
        if self._clean_up_triggered:
            return
        logger.info("Running cleanup task...")
        self._clean_up_triggered = True
        await self._cleanup_function()

    async def stop_and_cleanup(self):
        self.stop()
        await self._cleanup()

    def run(self, interval_seconds: int = 1):
        self._should_run = True
        loop = asyncio.get_running_loop()
        loop.create_task(self.event_loop(interval_seconds))
        loop.create_task(self.handle_signals())
