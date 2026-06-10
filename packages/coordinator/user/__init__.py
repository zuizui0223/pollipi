import asyncio

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel, Field

from constants import Codes, getDescription, getDescriptionHttp
from config import AppConfig
from user.model import User, create_user, authenticate_user, initialize_db
from user.auth import create_jwt_token, CurrentUser

from base import app, BaseResponseModel, TokenResponseModel
from constants import Token


class RegisterForm(BaseModel):
    email: str
    username: str
    password: str


class LoginForm(BaseModel):
    username: str
    password: str


class ChangePasswordForm(BaseModel):
    pwdOld: str
    pwdNew: str


class ChangeInfoForm(BaseModel):
    username: str


class UserProfileModel(BaseModel):
    email: str
    username: str
    group: str


class UserProfileResponseModel(BaseResponseModel):
    user: Optional[UserProfileModel] = None


@app.post("/api/user/login", response_model_exclude_none=True)
async def login(
    form_data: LoginForm,
) -> TokenResponseModel:
    email = form_data.username
    password = form_data.password
    # Use your existing authentication function
    code, user = await authenticate_user(email, password)

    if code == Codes.DONE:
        assert user is not None
        refresh_token = create_jwt_token(user, Token.Refresh, AppConfig.RefreshTokenExpires)
        access_token = create_jwt_token(user, Token.Access.General, AppConfig.AccessTokenExpires)
        return TokenResponseModel(
            access_token=access_token,
            tokens={str(Token.Refresh): refresh_token}
        )

    else:
        _, desc, status = getDescription(code)
        raise HTTPException(status_code=status, detail=desc)


@app.post("/api/user/refresh", response_model_exclude_none=True)
async def refresh(
    user: User = Depends(CurrentUser(Token.Refresh)),
) -> TokenResponseModel:
    access_token = create_jwt_token(user, Token.Access.General, AppConfig.AccessTokenExpires)
    return TokenResponseModel(
        access_token=access_token,
    )


@app.get("/api/user/me", response_model_exclude_none=True)
async def get_me(
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> UserProfileResponseModel:
    return UserProfileResponseModel(
        user=UserProfileModel(
            email=user.email,
            username=user.username,
            group=user.group,
        )
    )


@app.post("/api/user/register", response_model_exclude_none=True)
async def register(form_data: RegisterForm) -> BaseResponseModel:
    code = await create_user(form_data.email, form_data.username, form_data.password)
    if code == Codes.DONE:
        return BaseResponseModel()

    else:
        _, desc, status = getDescription(code)
        raise HTTPException(status_code=status, detail=desc)


@app.post("/api/user/pw/change", response_model_exclude_none=True)
async def change_password(
    form_data: ChangePasswordForm,
    user: User = Depends(CurrentUser(Token.Access.User.ChangeCriticalInfo)),
) -> BaseResponseModel:

    code, new_user = await authenticate_user(user.email, form_data.pwdOld)
    if code != Codes.DONE:
        return BaseResponseModel(**getDescriptionHttp(code))
    if not new_user or new_user.email != user.email:
        return BaseResponseModel(**getDescriptionHttp(Codes.ERR_WRONG_UNAME_OR_PW))

    code_upd = await user.set_password(form_data.pwdNew, True)
    return BaseResponseModel(**getDescriptionHttp(code_upd))


@app.post("/api/user/info/change", response_model_exclude_none=True)
async def change_info(
    form_data: ChangeInfoForm,
    user: User = Depends(CurrentUser(Token.Access.User.ChangeInfo)),
) -> BaseResponseModel:

    code_upd = await user.set_username(form_data.username, True)
    return BaseResponseModel(**getDescriptionHttp(code_upd))


initialize_db()
