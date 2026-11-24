from fastapi import APIRouter, Response, status

from backend.auth.depends import (
    AccessTokenDep,
    AuthServiceDep,
    CurrentUserDep,
    RefreshTokenDep,
)
from backend.auth.schemas import CredentialsSchema, UserSchema

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    credentials: CredentialsSchema, service: AuthServiceDep, response: Response
):
    return await service.register(credentials=credentials, response=response)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    credentials: CredentialsSchema, service: AuthServiceDep, response: Response
):
    return await service.login(credentials=credentials, response=response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    access: AccessTokenDep,
    refresh: RefreshTokenDep,
    service: AuthServiceDep,
    response: Response,
) -> None:
    await service.logout(access=access, refresh=refresh, response=response)


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    refresh: RefreshTokenDep, service: AuthServiceDep, response: Response
):
    return await service.refresh(refresh=refresh, response=response)


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify(user: CurrentUserDep) -> UserSchema:
    return UserSchema.model_validate(user)
