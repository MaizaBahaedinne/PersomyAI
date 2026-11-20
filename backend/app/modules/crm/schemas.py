import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)]
TextBody = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8000)]


class CompanyCreate(BaseModel):
    name: Name
    website: Short | None = None
    notes: TextBody = ""


class CompanyUpdate(BaseModel):
    name: Name | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None
    website: Short | None = None
    notes: TextBody | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    website: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


class CompanyPage(BaseModel):
    items: list[CompanyOut]
    total: int
    limit: int
    offset: int


class ContactCreate(BaseModel):
    company_id: uuid.UUID | None = None
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    status: Literal["LEAD", "ACTIVE", "INACTIVE"] = "LEAD"
    notes: TextBody = ""
    owner_user_id: uuid.UUID | None = None


class ContactUpdate(BaseModel):
    company_id: uuid.UUID | None = None
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    status: Literal["LEAD", "ACTIVE", "INACTIVE"] | None = None
    notes: TextBody | None = None
    owner_user_id: uuid.UUID | None = None


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    company_name: str | None = None
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    status: str
    notes: str
    owner_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ContactPage(BaseModel):
    items: list[ContactOut]
    total: int
    limit: int
    offset: int
