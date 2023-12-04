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


@app.get("/")
async def index_html():
    file = STATIC_FILES_PATH / "index.html"
    with open(file, "rb") as f:
        return HTMLResponse(content=f.read())


@app.get("/index.js")
async def index_js():
    file = STATIC_FILES_PATH / "index2.js"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/javascript")


@app.get("/style.css")
async def index_css():
    file = STATIC_FILES_PATH / "style.css"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/css")


@app.get("/index-1c12594a.css")
async def index_css():
    file = STATIC_FILES_PATH / "index-1c12594a.css"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/css")


@app.get("/index-4dd1a41d.js")
async def index_css():
    file = STATIC_FILES_PATH / "index-4dd1a41d.js"
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type="text/javascript")
