import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.crm import service
from app.modules.crm.schemas import (
    CompanyCreate,
    CompanyOut,
    CompanyPage,
    CompanyUpdate,
    ContactCreate,
    ContactOut,
    ContactPage,
    ContactUpdate,
)
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/crm", tags=["crm"])

Read = Depends(require_permission(Permission.CRM_READ))
Write = Depends(require_permission(Permission.CRM_WRITE))


@router.get("/companies", response_model=CompanyPage)
def list_companies(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern="^(ACTIVE|ARCHIVED)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    rows, total = service.list_companies(db, search=search, status=status, limit=limit, offset=offset)
    return CompanyPage(items=service.companies_out(rows), total=total, limit=limit, offset=offset)


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.create_company(db, ctx.user, payload, request)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.get_company(db, company_id)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    row = service.get_company(db, company_id)
    return service.update_company(db, ctx.user, row, payload, request)


@router.get("/contacts", response_model=ContactPage)
def list_contacts(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern="^(LEAD|ACTIVE|INACTIVE)$"),
    company_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    rows, total = service.list_contacts(
        db, search=search, status=status, company_id=company_id, limit=limit, offset=offset
    )
    return ContactPage(items=service.contacts_out(db, rows), total=total, limit=limit, offset=offset)


@router.post("/contacts", response_model=ContactOut, status_code=201)
def create_contact(payload: ContactCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.to_contact_out(db, service.create_contact(db, ctx.user, payload, request))


@router.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.to_contact_out(db, service.get_contact(db, contact_id))


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    row = service.get_contact(db, contact_id)
    return service.to_contact_out(db, service.update_contact(db, ctx.user, row, payload, request))
