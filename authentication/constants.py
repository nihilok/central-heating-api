import os

from fastapi.security import OAuth2PasswordBearer

LOCAL = True
origins = ["http://localhost:3000"]
ORIGINS = origins + ["*"] if LOCAL else origins


def _get_secret_key() -> str:
    secret_key = os.getenv("HEATING_API_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "Missing JWT secret key: set HEATING_API_SECRET_KEY (or SECRET_KEY)."
        )
    return secret_key


SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 5
USER_DB = f"{os.path.dirname(__file__)}/users.sqlite3"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
