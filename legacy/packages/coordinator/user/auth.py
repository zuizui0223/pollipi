import asyncio
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.logger import logger
from aenum import EnumType

from typing import Optional, Tuple, Any

from config import AppConfig

from user.model import User, get_user, guest_user
from constants import Codes, getDescription, Token, hasAccess, UserGroup


def create_jwt_token(
    data: User, token_type: Any = Token.Refresh, expires_delta: Optional[timedelta] = None
):
    token_type_val = token_type.value if hasattr(token_type, "value") else str(token_type)
    to_encode = {"sub": data.email, "name": data.username, "type": token_type_val}
    utcnow = datetime.now(tz=timezone.utc)
    if expires_delta:
        expire = utcnow + expires_delta
    else:
        expire = utcnow + AppConfig.AccessTokenExpires
    to_encode.update({"iat": utcnow, "exp": expire})
    encoded_jwt = jwt.encode(to_encode, AppConfig.JwtSecretKey, algorithm="HS256")
    return encoded_jwt


async def verify_jwt_token(token: str, token_type: Optional[str] = None):
    if not token:
        return None, True
    try:
        payload = jwt.decode(token, AppConfig.JwtSecretKey, algorithms=["HS256"])
    except JWTError:
        return None, True  # the token is invalid
    email = payload.get("sub")
    iat = payload.get("iat")
    if not email or iat is None:
        return None, True
    issue_time = datetime.fromtimestamp(float(iat), tz=timezone.utc)
    user = await get_user(email)
    if user is not None:
        tokens_valid_after = user.tokens_valid_after
        if tokens_valid_after.tzinfo is None:
            tokens_valid_after = tokens_valid_after.replace(tzinfo=timezone.utc)
        # Truncate microsecond precision to match JWT iat integer second precision
        tokens_valid_after = tokens_valid_after.replace(microsecond=0)
        issue_time = issue_time.replace(microsecond=0)
        if tokens_valid_after > issue_time:
            return None, True  # the token is expired/invalidated
    if token_type is not None and token_type != payload.get("type"):
        return user, False  # wrong type
    return user, True


async def verify_and_authorize_token(token: str, required_type: Optional[str] = None) -> Tuple[Optional[User], bool]:
    """
    Verifies a JWT token signature, expiration, tokens_valid_after,
    and checks if the user has the required access type.
    """
    if not token:
        return None, False
    try:
        payload = jwt.decode(token, AppConfig.JwtSecretKey, algorithms=["HS256"])
    except JWTError:
        return None, False

    email = payload.get("sub")
    iat = payload.get("iat")
    if not email or iat is None:
        return None, False

    user = await get_user(email)
    if user is None:
        return None, False

    # Check iat >= user.tokens_valid_after
    issue_time = datetime.fromtimestamp(float(iat), tz=timezone.utc)
    tokens_valid_after = user.tokens_valid_after
    if tokens_valid_after.tzinfo is None:
        tokens_valid_after = tokens_valid_after.replace(tzinfo=timezone.utc)
    # Truncate microsecond precision to match JWT iat integer second precision
    tokens_valid_after = tokens_valid_after.replace(microsecond=0)
    issue_time = issue_time.replace(microsecond=0)
    
    if tokens_valid_after > issue_time:
        return None, False

    jwt_type = payload.get("type")

    # If required_type is specified:
    if required_type is not None:
        req_type_str = getattr(required_type, "value", str(required_type))
        jwt_type_str = ""
        if jwt_type is not None:
            jwt_type_str = getattr(jwt_type, "value", str(jwt_type))
        refresh_val = getattr(Token.Refresh, "value", "Token.Refresh")

        is_refresh_required = (req_type_str == refresh_val)
        is_refresh_token = (jwt_type_str == refresh_val)

        if is_refresh_required:
            if not is_refresh_token:
                return user, False
        else:
            # We require access permissions, so it cannot be a refresh token
            if is_refresh_token:
                return user, False
            # Check user group access
            if not hasAccess(user.group, required_type):
                return user, False

    return user, True


_, _af_desc, _af_code = getDescription(Codes.ERR_AUTH_FAILED)
_, _wt_desc, _wt_code = getDescription(Codes.ERR_WRONG_TOKEN_TYPE)


async def get_current_user(
    request: Request,
    response: Response,
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token", auto_error=False)),
    token_type: Optional[str] = None,
    hard: bool = True,
) -> Optional[User]:
    if not token:
        token = request.query_params.get("access_token") or request.cookies.get("pollipi_access_token") or ""
    user, is_authorized = await verify_and_authorize_token(token, token_type)

    guest_flag = token_type is not None and hasAccess(UserGroup.Guest, token_type)
    if (user is None or not is_authorized) and hard:
        if guest_flag:
            return guest_user
        if user is not None:
            raise HTTPException(
                status_code=403, detail="Permission denied"
            )
        raise HTTPException(
            _af_code, detail=_af_desc, headers={"WWW-Authenticate": "Bearer"}
        )

    return user if is_authorized else None


async def get_current_user_ws(
    token: str, token_type: Optional[str] = None, hard: bool = True
):
    user, is_authorized = await verify_and_authorize_token(token, token_type)
    guest_flag = token_type is not None and hasAccess(UserGroup.Guest, token_type)
    if user is None or not is_authorized:
        if not guest_flag and hard:
            return None
        return guest_user
    return user


class CurrentUser:
    """
    Get the current user based on the provided authentication token.

    Args:
        type (Optional[str], optional): The type of token, if specified. Defaults to None.
        hard (bool, optional): Whether to enforce strict authentication. Defaults to True.

    Raises:
        HTTPException: Raised when authentication fails.

    Returns:
        Optional[User]: The authenticated user if successful, else None.
    """

    def __init__(self, token_type: Optional[Any] = None, hard: bool = True):
        self.token_type = (
            token_type.value if token_type is not None and hasattr(token_type, "value") else token_type
        )
        self.hard = hard

    async def __call__(
        self,
        request: Request,
        response: Response,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="token", auto_error=False)),
    ):
        u = await get_current_user(request, response, token, self.token_type, self.hard)
        return u
