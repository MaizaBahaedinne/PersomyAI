from pydantic import BaseModel, Field


class FinanceSummary(BaseModel):
    task_runs_total: int
    cost_cents_total: int
    cost_cents_30d: int
    average_cost_cents: float


class FinanceSimulationIn(BaseModel):
    monthly_revenue_cents: int = Field(ge=0)
    gross_margin_percent: float = Field(ge=0, le=100)
    ai_cost_cents_monthly: int = Field(ge=0)
    growth_percent: float = Field(default=0, ge=-100, le=100)


class FinanceSimulationOut(BaseModel):
    projected_revenue_cents: int
    projected_margin_cents: int
    margin_after_ai_cents: int
    ai_cost_share_percent: float
