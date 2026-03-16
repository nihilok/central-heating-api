import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from application.constants import (
    RUN_EVENT_LOOP_ON_STARTUP,
    CHECK_FREQUENCY_SECONDS,
    CORS_ALLOWED_ORIGINS,
)
from application.event_loop import event_loop as heating_event_loop
from application.routes import router as api_router
from authentication.routes import router as auth_router

app = FastAPI()

app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

STATIC_FILES_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "front-end"

if RUN_EVENT_LOOP_ON_STARTUP:

    @app.on_event("startup")
    def start():
        heating_event_loop.run(CHECK_FREQUENCY_SECONDS)

    @app.on_event("shutdown")
    async def stop():
        await heating_event_loop.stop_and_cleanup()


app.mount("/static", StaticFiles(directory=STATIC_FILES_PATH), name="static")
app.mount("/", StaticFiles(directory=STATIC_FILES_PATH, html=True), name="frontend")
