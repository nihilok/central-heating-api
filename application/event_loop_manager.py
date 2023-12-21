import asyncio
import signal
from typing import Callable


class EventLoopManager:
    def __init__(
        self,
        event_loop_coroutine: Callable,
        cleanup_function: Callable,
        use_signals: bool = False,
    ):
        self._event_loop_coroutine = event_loop_coroutine
        self._cleanup_function = cleanup_function
        self._should_run = True
        self._clean_up_triggered = False
        self._use_signals = use_signals

    async def event_loop(self, interval: int):
        while self._should_run:
            await self._event_loop_coroutine()
            await asyncio.sleep(interval)

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
