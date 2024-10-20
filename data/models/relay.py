import time
from typing import Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict

from application.logs import log_exceptions
from lib.errors import CommunicationError
from lib.funcs import fetch_text


class UrlsDict(TypedDict):
    on: str
    off: str


class RelayNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url_status: str
    cached_value: Optional[bool] = None
    last_updated: float = 0
    expiry_time: int = 10
    URLS: UrlsDict

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.URLS = {"on": f"{self.URLS[True]}", "off": f"{self.URLS[False]}"}
        except KeyError:
            pass

    @log_exceptions("models.RelayNode")
    async def hit_switch(self, url):
        if not await fetch_text(url):
            raise CommunicationError(f"Failed to hit switch at {url}")

    @log_exceptions("models.RelayNode")
    async def switch(self, direction="off"):
        try:
            url = self.URLS[direction]
            return await self.hit_switch(url)
        except KeyError:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions("models.RelayNode")
    async def status(self) -> Optional[bool]:
        if (
            self.cached_value is not None
            and self.last_updated + self.expiry_time > time.time()
        ):
            return self.cached_value

        resp = await fetch_text(f"{self.url_status}")
        if resp is None:
            raise CommunicationError(f"Failed to get status from {self.url_status}")

        self.cached_value = not int(resp)
        self.last_updated = time.time()
        return self.cached_value
