import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from application.constants import RUN_EVENT_LOOP_ON_STARTUP, CHECK_FREQUENCY_SECONDS
from application.event_loop import event_loop as heating_event_loop
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
        heating_event_loop.run(CHECK_FREQUENCY_SECONDS)

    @app.on_event("shutdown")
    async def stop():
        await heating_event_loop.stop_and_cleanup()


async def static_response(filename, media_type="text/html"):
    file = STATIC_FILES_PATH / filename
    with open(file, "rb") as f:
        return Response(content=f.read(), media_type=media_type)


app.mount("/static", StaticFiles(directory=STATIC_FILES_PATH), name="static")


@app.get("/")
async def index_html():
    return await static_response("index.html")


@app.get("/assets/flame-b2dd84ec.png")
async def flame_icon():
    return await static_response("assets/flame-b2dd84ec.png", "image/png")
