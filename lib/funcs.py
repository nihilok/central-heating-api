from typing import Optional, Union

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


async def send_request(url) -> Union[ClientResponse, EmptyResponse]:
    result = EmptyResponse
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.ok:
                    result = response

    except ClientConnectionError as e:
        get_logger(__name__).error(e)

    return result


async def fetch_json(url) -> Optional[dict]:
    return await (await send_request(url)).json()


async def fetch_text(url) -> Optional[str]:
    return await (await send_request(url)).text()
