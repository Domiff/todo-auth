from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CredentialsSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access: str
    type: str = "bearer"


class UserSchema(BaseModel):
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
