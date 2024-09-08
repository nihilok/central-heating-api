import aiohttp
from aiohttp import ClientConnectionError

from application.logs import get_logger


async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.ok:
                    return await response.json()

    except ClientConnectionError as e:
        get_logger(__name__).error(e)


async def fetch_text(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.ok:
                return await response.text()
