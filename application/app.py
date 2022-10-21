import os
from pathlib import Path

from fastapi import FastAPI
from starlette.responses import HTMLResponse, Response

from application.constants import RUN_EVENT_LOOP_ON_STARTUP
from application.event_loop import run_async_loop, stop_async_loop
from application.routes import router as api_router

app = FastAPI()

app.include_router(api_router)

STATIC_FILES_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "front-end"

if RUN_EVENT_LOOP_ON_STARTUP:

    @app.on_event("startup")
    def start():
        run_async_loop()

    @app.on_event("shutdown")
    async def stop():
        await stop_async_loop()


@app.get("/")
async def index():
    file = STATIC_FILES_PATH / "index.html"
    with open(file, "rb") as f:
        return HTMLResponse(content=f.read())


@app.get("/index.js")
async def index():
    file = STATIC_FILES_PATH / "index.js"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/javascript")


@app.get("/style.css")
async def index():
    file = STATIC_FILES_PATH / "style.css"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/css")
