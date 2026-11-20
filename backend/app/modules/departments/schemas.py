from pydantic import BaseModel


class DepartmentSummary(BaseModel):
    code: str
    agents_total: int
    agents_active: int
    agents_paused: int


class DepartmentsOut(BaseModel):
    items: list[DepartmentSummary]
