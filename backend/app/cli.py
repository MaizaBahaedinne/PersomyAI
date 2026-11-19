"""Commandes d'administration.

Création sécurisée d'un administrateur humain (aucun mot de passe par défaut) :
    python -m app.cli create-admin --email prenom@exemple.com --name "Prénom Nom"
Le mot de passe est demandé de façon interactive (non affiché, jamais dans l'historique shell).
"""

import argparse
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

import app.models  # noqa: F401  (enregistre tous les modèles)
from app.core.db import new_session
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.users.models import User
from app.modules.users.schemas import PASSWORD_MAX, validate_password_strength


def create_admin(email: str, name: str, password: str, language: str = "fr") -> User:
    email = TypeAdapter(EmailStr).validate_python(email).strip().lower()
    validate_password_strength(password, email)
    if len(password) > PASSWORD_MAX:
        raise ValueError("Password too long")
    with new_session() as db:
        if db.query(User).filter(User.email == email).first():
            raise ValueError(f"A user with email {email} already exists")
        user = User(
            email=email,
            display_name=name.strip(),
            password_hash=hash_password(password),
            role="SUPER_ADMIN",
            preferred_language=language,
            is_active=True,
        )
        db.add(user)
        db.flush()
        audit.record(
            db, "user.bootstrap_admin", actor_label="cli", target_type="user", target_id=user.id,
            details={"email": email, "role": "SUPER_ADMIN"},
        )
        db.commit()
        return user


def _prompt_password() -> str:
    first = getpass.getpass("Password (min 12 chars): ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise ValueError("Passwords do not match")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create a SUPER_ADMIN account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    admin.add_argument("--language", choices=["fr", "en"], default="fr")
    args = parser.parse_args(argv)

    try:
        password = _prompt_password()
        user = create_admin(args.email, args.name, password, args.language)
    except (ValueError, ValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"SUPER_ADMIN created: {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
