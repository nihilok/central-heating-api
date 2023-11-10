import time
from datetime import timedelta, datetime

import aiosqlite
from fastapi import Depends
from jose import jwt, JWTError
from passlib.context import CryptContext

from authentication.constants import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    ALGORITHM,
    USER_DB, oauth2_scheme,
)
from authentication.token_models import TokenData
from authentication.exceptions import credentials_exception

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(password, hash):
    return pwd_context.verify(password, hash)


async def replace(model, values: dict, db_path=USER_DB):
    table = model.__table__
    values = values.items()
    stmt = f"""
    REPLACE INTO {table} ({', '.join((v[0] for v in values))})
    VALUES ({', '.join(("'" + v[1] + "'" for v in values))});
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(stmt)
        await db.commit()


def create_access_token(data: dict):
    to_encode = data.copy()
    expires_delta = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except Exception:
        return {"message": "token expired, please log in again"}


async def get_data_from_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data
