from pydantic import BaseModel


class TeamMember(BaseModel):
    id: str
    display_name: str
    email: str
    role: str
    is_active: bool
    preferred_language: str
    two_factor_enabled: bool
    last_login_at: str | None


class TeamSummary(BaseModel):
    total: int
    active: int
    disabled: int
    super_admins: int
    with_two_factor: int


class TeamOut(BaseModel):
    summary: TeamSummary
    items: list[TeamMember]
