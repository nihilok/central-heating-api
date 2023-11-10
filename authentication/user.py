from typing import Optional

import aiosqlite
from fastapi import Depends
from pydantic import BaseModel, constr, ValidationError

from authentication.constants import USER_DB, oauth2_scheme
from authentication.exceptions import credentials_exception
from authentication.funcs import replace, get_data_from_token
from authentication.funcs import get_password_hash as _hash
from authentication.funcs import verify_password as _verify


class User(BaseModel):
    __table__ = "users"
    username: str
    password: str

    def check_password(self, password):
        return _verify(password, self.password)

    @staticmethod
    def _hash(password):
        return _hash(password)

    @classmethod
    async def get(cls, username):
        async with aiosqlite.connect(USER_DB) as db:
            async with db.execute(
                f"SELECT * FROM users WHERE username = '{username}'"
            ) as cursor:
                from_db = await cursor.fetchone()
                if from_db is None:
                    return None
                return cls(username=from_db[0], password=from_db[1])

    async def save(self):
        if len(self.password) != 60:
            self.password = self._hash(self.password)
        await replace(User, {"username": self.username, "password": self.password})

    @classmethod
    async def create(cls, username: str, password: constr(max_length=59)):
        password = cls._hash(password)
        await replace(User, {"username": username, "password": password})
        return cls(username=username, password=password)

    async def update_password(self, old_password, password: constr(max_length=59)):
        if not self.check_password(old_password):
            raise ValidationError("Incorrect password")
        self.password = self._hash(password)
        await self.save()

    @classmethod
    async def authenticate_user(cls, username: str, password: str) -> Optional["User"]:
        user = await cls.get(username=username)
        try:
            if not _verify(password, user.password):
                raise credentials_exception
            return user
        except Exception:
            raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme)):
    data = await get_data_from_token(token)
    user = await User.get(username=data.username)
    if user is None:
        raise credentials_exception
    return user


def run(coroutine):
    import asyncio
    return asyncio.run(coroutine)
