import uuid

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.modules.audit import service as audit
from app.modules.crm.models import Company, Contact
from app.modules.crm.schemas import CompanyCreate, CompanyOut, CompanyUpdate, ContactCreate, ContactOut, ContactUpdate
from app.modules.users.models import User


def get_company(db: Session, company_id: uuid.UUID) -> Company:
    row = db.get(Company, company_id)
    if not row:
        raise NotFound("Company not found", code="company_not_found")
    return row


def get_contact(db: Session, contact_id: uuid.UUID) -> Contact:
    row = db.get(Contact, contact_id)
    if not row:
        raise NotFound("Contact not found", code="contact_not_found")
    return row


def _check_company_name(db: Session, name: str, exclude_id: uuid.UUID | None = None) -> None:
    stmt = select(Company.id).where(func.lower(Company.name) == name.lower())
    if exclude_id:
        stmt = stmt.where(Company.id != exclude_id)
    if db.scalar(stmt):
        raise Conflict("Company name already exists", code="company_name_taken")


def create_company(db: Session, actor: User, payload: CompanyCreate, request: Request) -> Company:
    _check_company_name(db, payload.name)
    row = Company(**payload.model_dump(), created_by=actor.id)
    db.add(row)
    db.flush()
    audit.record(
        db,
        "crm.company.create",
        request=request,
        actor=actor,
        target_type="crm_company",
        target_id=row.id,
        details={"name": row.name},
    )
    db.commit()
    return row


def update_company(db: Session, actor: User, row: Company, payload: CompanyUpdate, request: Request) -> Company:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row
    if "name" in changes:
        _check_company_name(db, changes["name"], exclude_id=row.id)
    for key, value in changes.items():
        setattr(row, key, value)
    audit.record(
        db,
        "crm.company.update",
        request=request,
        actor=actor,
        target_type="crm_company",
        target_id=row.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    return row


def list_companies(db: Session, *, search: str | None, status: str | None, limit: int, offset: int) -> tuple[list[Company], int]:
    stmt = select(Company)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(Company.name).like(like))
    if status:
        stmt = stmt.where(Company.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(func.lower(Company.name)).limit(limit).offset(offset)).all()
    return list(rows), total


def _contact_company_name(db: Session, company_id: uuid.UUID | None) -> str | None:
    if not company_id:
        return None
    row = db.get(Company, company_id)
    return row.name if row else None


def to_contact_out(db: Session, row: Contact) -> ContactOut:
    out = ContactOut.model_validate(row)
    out.company_name = _contact_company_name(db, row.company_id)
    return out


def create_contact(db: Session, actor: User, payload: ContactCreate, request: Request) -> Contact:
    data = payload.model_dump()
    if data.get("company_id"):
        get_company(db, data["company_id"])
    row = Contact(**data, created_by=actor.id)
    db.add(row)
    db.flush()
    audit.record(
        db,
        "crm.contact.create",
        request=request,
        actor=actor,
        target_type="crm_contact",
        target_id=row.id,
        details={"name": f"{row.first_name} {row.last_name}"},
    )
    db.commit()
    return row


def update_contact(db: Session, actor: User, row: Contact, payload: ContactUpdate, request: Request) -> Contact:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row
    if "company_id" in changes and changes["company_id"] is not None:
        get_company(db, changes["company_id"])
    for key, value in changes.items():
        setattr(row, key, value)
    audit.record(
        db,
        "crm.contact.update",
        request=request,
        actor=actor,
        target_type="crm_contact",
        target_id=row.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    return row


def list_contacts(
    db: Session,
    *,
    search: str | None,
    status: str | None,
    company_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Contact], int]:
    stmt = select(Contact)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Contact.first_name).like(like),
                func.lower(Contact.last_name).like(like),
                func.lower(func.coalesce(Contact.email, "")).like(like),
            )
        )
    if status:
        stmt = stmt.where(Contact.status == status)
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(func.lower(Contact.last_name), func.lower(Contact.first_name)).limit(limit).offset(offset)).all()
    return list(rows), total


def contacts_out(db: Session, rows: list[Contact]) -> list[ContactOut]:
    return [to_contact_out(db, r) for r in rows]


def companies_out(rows: list[Company]) -> list[CompanyOut]:
    return [CompanyOut.model_validate(r) for r in rows]
