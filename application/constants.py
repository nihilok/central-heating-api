import os

THERMOSTAT_THRESHOLD = 0.2
CHECK_FREQUENCY_SECONDS = 10
DEFAULT_MINIMUM_TARGET = 5
# set the below to False in order to run the app in "test mode"
# this skips all the temperature checking and relay switching logic carried out by the main task in event_loop.py
RUN_EVENT_LOOP_ON_STARTUP = True


def _parse_cors_origins() -> list[str]:
    raw = os.getenv(
        "HEATING_API_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError(
            "HEATING_API_CORS_ORIGINS must contain at least one comma-separated origin."
        )
    return origins


CORS_ALLOWED_ORIGINS = _parse_cors_origins()
