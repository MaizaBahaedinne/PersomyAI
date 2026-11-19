import pytest
from sqlalchemy import inspect, select

from app.cli import create_admin
from app.modules.audit.models import AuditEvent
from app.modules.users.models import User


def test_create_admin_creates_super_admin_with_hashed_password(db):
    user = create_admin("Boss@Example.com", "Boss", "Very-Strong-Pass-1")
    stored = db.scalars(select(User)).one()
    assert stored.email == "boss@example.com" and stored.role == "SUPER_ADMIN"
    assert stored.password_hash.startswith("$argon2id$")
    assert user.id == stored.id
    event = db.scalars(select(AuditEvent)).one()
    assert event.action == "user.bootstrap_admin" and "Very-Strong" not in str(event.details)


def test_create_admin_rejects_weak_password_and_duplicates(db):
    with pytest.raises(ValueError):
        create_admin("a@example.com", "A", "short")
    create_admin("a@example.com", "A", "Very-Strong-Pass-1")
    with pytest.raises(ValueError):
        create_admin("A@example.com", "A2", "Very-Strong-Pass-2")


def test_no_default_admin_exists(db):
    assert db.scalars(select(User)).all() == []


def test_migrations_match_models(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    from app.core.config import get_settings

    url = f"sqlite:///{tmp_path / 'migr.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "auth_sessions", "login_attempts", "audit_events", "system_settings"} <= tables
    assert {"agents", "agent_permissions", "agent_tools"} <= tables
    command.check(cfg)  # échoue si les modèles divergent de la migration
    command.downgrade(cfg, "base")
    get_settings.cache_clear()
