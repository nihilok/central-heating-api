from typing import Optional, Union, AsyncGenerator

import aiohttp
from aiohttp import ClientConnectionError, ClientResponse

from application.logs import get_logger


class EmptyResponse:
    @staticmethod
    async def json() -> Optional[dict]:
        return None

    @staticmethod
    async def text() -> Optional[str]:
        return None


async def send_request(url) -> AsyncGenerator[Union[ClientResponse, EmptyResponse]]:
    result = EmptyResponse
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.ok:
                    yield response

    except ClientConnectionError as e:
        get_logger(__name__).error(e)

    yield result


async def fetch_json(url) -> Optional[dict]:
    async for response in send_request(url):
        return await response.json()


async def fetch_text(url) -> Optional[str]:
    async for response in send_request(url):
        return await response.text()
