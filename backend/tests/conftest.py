import os

from cryptography.fernet import Fernet

# Doit être positionné avant l'import de l'application.
os.environ["APP_ENV"] = "test"
os.environ["TWO_FACTOR_KEY"] = Fernet.generate_key().decode()
os.environ["COOKIE_SECURE"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TRUSTED_ORIGINS"] = "http://localhost:3000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.core import db as dbmod  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.users.models import User  # noqa: E402

PASSWORD = "Correct-Horse-42x"


@pytest.fixture()
def engine():
    get_settings.cache_clear()
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    dbmod.Base.metadata.create_all(eng)
    dbmod.configure_engine(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    session = dbmod.new_session()
    yield session
    session.close()


@pytest.fixture()
def client(engine):
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def make_user(db):
    def _make(email="user@example.com", role="VIEWER", password=PASSWORD, active=True, name="Test User"):
        user = User(
            email=email, display_name=name, password_hash=hash_password(password), role=role,
            is_active=active, preferred_language="fr",
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture()
def login(engine):
    """Retourne une fonction qui ouvre une session distincte (client indépendant) pour un utilisateur."""
    clients = []

    def _login(email, password=PASSWORD):
        c = TestClient(create_app())
        clients.append(c)
        r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = c.cookies.get("persomy_csrf")
        return c

    yield _login
    for c in clients:
        c.close()
