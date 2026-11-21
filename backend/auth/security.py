from datetime import timedelta

import jwt
from authx import AuthX, AuthXConfig

from backend.core.settings import settings
from backend.infrastructures.redis import key_builder, redis

config = AuthXConfig(
    JWT_ALGORITHM=settings.auth.JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=settings.auth.JWT_ACCESS_TOKEN_EXPIRES),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(
        seconds=settings.auth.JWT_REFRESH_TOKEN_EXPIRES
    ),
    JWT_TOKEN_LOCATION=["headers", "cookies"],
    JWT_PRIVATE_KEY=settings.auth.JWT_PRIVATE_KEY.read_text(),
    JWT_PUBLIC_KEY=settings.auth.JWT_PUBLIC_KEY.read_text(),
)
auth = AuthX(config=config)


@auth.set_callback_token_blocklist
async def is_token_revoked(token: str) -> bool:
    try:
        payload = jwt.decode(
            token,
            config.public_key,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except jwt.InvalidTokenError:
        return False

    jti = payload.get("jti")

    if jti is None:
        return False

    return await redis.exists(key_builder("auth:revoked", jti)) > 0
