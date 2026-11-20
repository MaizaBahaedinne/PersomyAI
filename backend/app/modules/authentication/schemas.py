import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.users.schemas import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    Language,
    UserOut,
    validate_password_strength,
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    # Code TOTP à 6 chiffres ou code de secours ; requis seulement si la 2FA est activée.
    otp: Optional[str] = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class MeOut(BaseModel):
    user: UserOut
    permissions: list[str]


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    @field_validator("new_password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)


class PreferencesUpdate(BaseModel):
    preferred_language: Optional[Language] = None
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)


class TwoFactorStatus(BaseModel):
    enabled: bool
    available: bool
    recovery_codes_left: int


class TwoFactorSetupIn(BaseModel):
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class TwoFactorSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg_data_uri: str


class TwoFactorCodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class TwoFactorConfirmIn(TwoFactorCodeIn):
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool = False
