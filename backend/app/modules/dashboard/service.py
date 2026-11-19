from datetime import timedelta
from time import perf_counter

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.agents import service as agents_service
from app.modules.audit.models import AuditEvent
from app.modules.authentication.models import AuthSession
from app.modules.orchestration import service as orchestration_service
from app.modules.settings.service import get_settings_values
from app.modules.users.models import User

# Modules dont les données n'existent pas encore : jamais de chiffres fictifs.
PENDING_MODULES = ["automations"]

FAILED_LOGIN_ALERT_THRESHOLD = 10


def _count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def database_status(db: Session) -> dict:
    start = perf_counter()
    try:
        db.execute(text("SELECT 1"))
        return {"name": "database", "status": "ok", "latency_ms": round((perf_counter() - start) * 1000, 1)}
    except Exception:
        return {"name": "database", "status": "down", "latency_ms": None}


def build_summary(db: Session) -> dict:
    now = utcnow()
    since = now - timedelta(hours=24)

    total_users = _count(db, select(func.count()).select_from(User))
    active_users = _count(db, select(func.count()).select_from(User).where(User.is_active.is_(True)))
    super_admins = _count(
        db,
        select(func.count()).select_from(User).where(User.role == "SUPER_ADMIN", User.is_active.is_(True)),
    )
    active_sessions = _count(
        db,
        select(func.count()).select_from(AuthSession).where(
            AuthSession.revoked_at.is_(None), AuthSession.expires_at > now
        ),
    )

    def audit_count(action: str, status: str | None = None) -> int:
        stmt = select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == action, AuditEvent.created_at >= since
        )
        if status:
            stmt = stmt.where(AuditEvent.status == status)
        return _count(db, stmt)

    logins_ok = audit_count("auth.login")
    logins_failed = audit_count("auth.login.failed")
    throttled = audit_count("auth.login.blocked")

    alerts = []
    if logins_failed >= FAILED_LOGIN_ALERT_THRESHOLD:
        alerts.append({"code": "failed_logins_high", "severity": "warning", "count": logins_failed})
    if throttled:
        alerts.append({"code": "login_throttled", "severity": "warning", "count": throttled})
    if super_admins < 2:
        alerts.append({"code": "single_super_admin", "severity": "info", "count": super_admins})

    agents = agents_service.status_counts(db)
    emergency = agents_service.emergency_state(db)["active"]
    if emergency:
        alerts.append({"code": "emergency_stop_active", "severity": "warning", "count": 1})
    if agents["error"]:
        alerts.append({"code": "agents_in_error", "severity": "warning", "count": agents["error"]})
    tasks = orchestration_service.task_counts(db)
    if tasks["awaiting_approval"]:
        alerts.append({"code": "tasks_awaiting_approval", "severity": "info", "count": tasks["awaiting_approval"]})

    recent = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10)).all()
    security_events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.status == "failure", AuditEvent.created_at >= since)
        .order_by(AuditEvent.created_at.desc())
        .limit(5)
    ).all()

    return {
        "company": {"name": get_settings_values(db).company_name},
        "generated_at": now,
        "users": {"total": total_users, "active": active_users, "disabled": total_users - active_users,
                  "super_admins": super_admins},
        "sessions": {"active": active_sessions},
        "agents": agents,
        "tasks": tasks,
        "missions": orchestration_service.mission_counts(db),
        "emergency_stop": emergency,
        "security": {
            "logins_success_24h": logins_ok,
            "logins_failed_24h": logins_failed,
            "logins_throttled_24h": throttled,
            "recent_failures": recent_to_dicts(security_events),
        },
        "recent_activity": recent_to_dicts(recent),
        "alerts": alerts,
        "services": [{"name": "api", "status": "ok", "latency_ms": None}, database_status(db)],
        "pending_modules": PENDING_MODULES,
    }


def recent_to_dicts(events) -> list[dict]:
    return [
        {
            "id": e.id,
            "created_at": e.created_at,
            "action": e.action,
            "actor_label": e.actor_label,
            "status": e.status,
        }
        for e in events
    ]
