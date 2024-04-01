import aiohttp


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.ok:
                return await response.json()


async def fetch_text(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.ok:
                return await response.text()
