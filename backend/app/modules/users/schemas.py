import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RoleName = Literal["SUPER_ADMIN", "ADMIN", "OPERATOR", "VIEWER"]
Language = Literal["fr", "en"]

PASSWORD_MIN = 12
PASSWORD_MAX = 128


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_password_strength(password: str, email: str | None = None) -> str:
    if len(password) < PASSWORD_MIN:
        raise ValueError(f"Password must contain at least {PASSWORD_MIN} characters")
    if password.strip() != password:
        raise ValueError("Password must not start or end with whitespace")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must contain letters and digits")
    if email and password.lower() == email.lower():
        raise ValueError("Password must differ from the email address")
    return password


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: RoleName
    is_active: bool
    preferred_language: Language
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    role: RoleName = "VIEWER"
    preferred_language: Language = "fr"

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name must not be blank")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None
    preferred_language: Optional[Language] = None


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    @field_validator("new_password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int
