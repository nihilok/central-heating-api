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
    ):
        self._event_loop_coroutine = event_loop_coroutine
        self._cleanup_function = cleanup_function
        self._should_run = True
        self._clean_up_triggered = False
        self._use_signals = use_signals
        self._auto_restart = auto_restart

    async def event_loop(self, interval: int):
        try:
            while self._should_run:
                await self._event_loop_coroutine()
                await asyncio.sleep(interval)
        except Exception as e:
            logger.error(e, exc_info=True)
            if not self._auto_restart:
                raise

            try:
                await self._cleanup()
            except Exception as e:
                logger.error(f"Cleanup on auto-restart failed: {e}", exc_info=True)
            if self._should_run:
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
