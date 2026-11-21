from typing import Annotated

from authx import RequestToken
from authx.exceptions import RevokedTokenError
from fastapi import Depends, Request

from backend.auth.exceptions import Unauthorized
from backend.auth.models import User
from backend.auth.repository import UserRepository
from backend.auth.security import auth
from backend.auth.service import AuthService
from backend.core.depends import SessionDep


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


async def get_current_user(request: Request, session: SessionDep) -> User:
    token = await auth.get_access_token_from_request(
        request=request, locations=["headers"]
    )

    if await auth.is_token_in_blocklist(token.token):
        raise RevokedTokenError("Token has been revoked")

    payload = auth.verify_token(token, verify_csrf=False)
    user = await UserRepository(session).get_by_id(int(payload.sub))

    if user is None or not user.is_active:
        raise Unauthorized("Invalid token")

    return user


async def get_access_token(request: Request) -> RequestToken:
    return await auth.get_access_token_from_request(
        request=request, locations=["headers"]
    )


async def get_refresh_token(request: Request) -> RequestToken:
    return await auth.get_refresh_token_from_request(
        request=request, locations=["cookies"]
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AccessTokenDep = Annotated[RequestToken, Depends(get_access_token)]
RefreshTokenDep = Annotated[RequestToken, Depends(get_refresh_token)]
