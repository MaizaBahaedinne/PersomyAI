from typing import Optional

from fastapi import Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import service as audit
from app.modules.settings.models import SystemSetting
from app.modules.users.models import User
from app.modules.users.schemas import Language

DEFAULTS = {"company_name": "Persomy AI", "default_language": "fr"}


class SettingsOut(BaseModel):
    company_name: str
    default_language: Language


class SettingsUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    default_language: Optional[Language] = None


def get_settings_values(db: Session) -> SettingsOut:
    stored = {row.key: row.value for row in db.scalars(select(SystemSetting)).all()}
    values = {**DEFAULTS, **{k: v for k, v in stored.items() if k in DEFAULTS}}
    return SettingsOut(**values)


def update_settings(db: Session, actor: User, data: SettingsUpdate, request: Request) -> SettingsOut:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        row = db.get(SystemSetting, key)
        if row:
            row.value = value
            row.updated_by = actor.id
        else:
            db.add(SystemSetting(key=key, value=value, updated_by=actor.id))
    if changes:
        audit.record(
            db, "settings.update", request=request, actor=actor, target_type="settings",
            details={"keys": sorted(changes)},
        )
    db.commit()
    return get_settings_values(db)
