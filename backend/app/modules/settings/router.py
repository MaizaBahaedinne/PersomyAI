from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission
from app.modules.settings import service
from app.modules.settings.service import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def read_settings(
    ctx: AuthContext = Depends(require_permission(Permission.SETTINGS_READ)),
    db: Session = Depends(get_db),
):
    return service.get_settings_values(db)


@router.put("", response_model=SettingsOut)
def write_settings(
    payload: SettingsUpdate,
    request: Request,
    ctx: AuthContext = Depends(require_permission(Permission.SETTINGS_WRITE)),
    db: Session = Depends(get_db),
):
    return service.update_settings(db, ctx.user, payload, request)
