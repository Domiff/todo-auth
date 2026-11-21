import math

import jwt
from authx import RequestToken
from fastapi import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.exceptions import Unauthorized
from backend.auth.repository import UserRepository
from backend.auth.schemas import CredentialsSchema, TokenSchema
from backend.auth.security import auth
from backend.auth.utils import hash_password, verify_password
from backend.core.exceptions import AlreadyExists
from backend.core.logging import get_logger
from backend.core.settings import settings
from backend.infrastructures.redis import key_builder, redis

logger = get_logger(__name__)


class AuthService:
    _DUMMY_PASSWORD_HASH = hash_password("dummy")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(self.session)

    @staticmethod
    def _authenticate(user_id: int, response: Response) -> TokenSchema:
        token_pair = auth.create_token_pair(uid=str(user_id))
        auth.set_refresh_cookies(
            token_pair.refresh_token,
            response,
            max_age=settings.auth.JWT_REFRESH_TOKEN_EXPIRES,
        )
        return TokenSchema(access=token_pair.access_token)

    @staticmethod
    async def _revoke(jti: str, ttl: float, nx: bool = False) -> bool:
        return await redis.set(
            key_builder("auth:revoked", jti), "1", max(1, math.ceil(ttl)), nx=nx
        )

    async def register(
        self, credentials: CredentialsSchema, response: Response
    ) -> TokenSchema:
        data = {
            "email": credentials.email,
            "password": hash_password(credentials.password),
        }
        try:
            user = await self.user_repo.create(data)
        except IntegrityError as e:
            logger.error("User already exists", extra={"email": credentials.email})
            raise AlreadyExists() from e

        logger.info("User created successfully", extra={"user_id": user.id})

        return self._authenticate(user.id, response)

    async def login(
        self, credentials: CredentialsSchema, response: Response
    ) -> TokenSchema:
        user = await self.user_repo.get_by_email(credentials.email)

        if user is None:
            verify_password(credentials.password, self._DUMMY_PASSWORD_HASH)
            logger.warning(
                "Login failed: user does not exist", extra={"email": credentials.email}
            )
            raise Unauthorized("Invalid credentials")

        if not verify_password(credentials.password, user.password):
            logger.warning(
                "Login failed: password mismatch", extra={"user_id": user.id}
            )
            raise Unauthorized("Invalid credentials")

        if not user.is_active:
            logger.warning("Login failed: user is inactive", extra={"user_id": user.id})
            raise Unauthorized("Invalid credentials")

        logger.info("User logged in", extra={"user_id": user.id})

        return self._authenticate(user.id, response)

    async def logout(
        self, access: RequestToken, refresh: RequestToken, response: Response
    ) -> None:
        refresh_payload = auth.verify_token(refresh)

        try:
            access_payload = jwt.decode(
                access.token,
                auth.config.public_key,
                algorithms=[auth.config.JWT_ALGORITHM],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError as e:
            logger.warning("Logout failed: invalid access token")
            raise Unauthorized("Invalid token") from e

        if (
            access_payload.get("type") != "access"
            or access_payload.get("sub") != refresh_payload.sub
            or not access_payload.get("jti")
            or not refresh_payload.jti
        ):
            logger.warning(
                "Logout failed: token mismatch", extra={"user_id": refresh_payload.sub}
            )
            raise Unauthorized("Invalid token")

        auth.unset_refresh_cookies(response)

        await self._revoke(
            access_payload.get("jti"), settings.auth.JWT_ACCESS_TOKEN_EXPIRES
        )
        await self._revoke(
            refresh_payload.jti, refresh_payload.time_until_expiry.total_seconds()
        )
        logger.info("User logged out", extra={"user_id": refresh_payload.sub})

    async def refresh(self, refresh: RequestToken, response: Response) -> TokenSchema:
        payload = auth.verify_token(token=refresh)

        if not payload.jti:
            raise Unauthorized("Invalid token")

        if not await self._revoke(
            payload.jti, payload.time_until_expiry.total_seconds(), nx=True
        ):
            logger.warning(
                "Refresh failed: token already used", extra={"user_id": payload.sub}
            )
            raise Unauthorized("Invalid token")

        user = await self.user_repo.get_by_id(int(payload.sub))

        if user is None or not user.is_active:
            logger.warning(
                "Refresh failed: user unavailable", extra={"user_id": payload.sub}
            )
            raise Unauthorized("Invalid token")

        logger.info("Tokens refreshed", extra={"user_id": user.id})

        return self._authenticate(user.id, response)
