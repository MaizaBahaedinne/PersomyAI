import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('SUPER_ADMIN','ADMIN','OPERATOR','VIEWER')", name="ck_users_role"),
        CheckConstraint("preferred_language IN ('fr','en')", name="ck_users_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Toujours stocké en minuscules (normalisé par les schémas / services).
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="VIEWER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preferred_language: Mapped[str] = mapped_column(String(5), nullable=False, default="fr")
    # 2FA (TOTP) : secret chiffré (Fernet), jamais renvoyé par l'API ; dernier pas de temps accepté (anti-rejeu).
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    two_factor_secret_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    two_factor_last_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
