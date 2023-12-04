import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, Response

from application.constants import RUN_EVENT_LOOP_ON_STARTUP
from application.event_loop import run_async_loop, stop_async_loop
from application.routes import router as api_router
from authentication.routes import router as auth_router

app = FastAPI()

app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_FILES_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "front-end"

if RUN_EVENT_LOOP_ON_STARTUP:

    @app.on_event("startup")
    def start():
        run_async_loop()

    @app.on_event("shutdown")
    async def stop():
        await stop_async_loop()


async def static_response(filename, media_type="text/html"):
    file = STATIC_FILES_PATH / filename
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type=media_type)


@app.get("/")
async def index_html():
    return await static_response("index.html", "text/html")


@app.get("/app.min.js")
async def index_js():
    return await static_response("app.min.js", "application/javascript")


@app.get("/main.css")
async def index_css():
    return await static_response("main.css", "text/css")
