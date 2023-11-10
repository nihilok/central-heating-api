import os

from fastapi.security import OAuth2PasswordBearer

LOCAL = True
origins = ["http://localhost:3000"]
ORIGINS = origins + ["*"] if LOCAL else origins
SECRET_KEY = "SoMeThInG_-sUp3Rs3kREt!!"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 5
USER_DB = f"{os.path.dirname(__file__)}/users.sqlite3"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
