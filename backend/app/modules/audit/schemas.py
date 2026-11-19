import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_user_id: Optional[uuid.UUID]
    actor_label: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[str]
    status: str
    ip_address: Optional[str]
    details: Optional[dict[str, Any]]


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int
