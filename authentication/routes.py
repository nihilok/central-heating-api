from fastapi import Depends, status, APIRouter
from starlette.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from authentication.funcs import (
    create_access_token,
)
from authentication.user import User, get_current_user
from authentication.token_models import Token

router = APIRouter()


@router.post("/token/", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = await User.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/check_token/")
async def check_token(
    user: User = Depends(get_current_user),
):
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")
