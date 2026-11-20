from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    users_total: int
    users_active: int
    users_with_2fa: int
    agents_total: int
    automations_total: int
    automations_active: int
    companies_total: int
    contacts_total: int
    tasks_total: int
    tasks_open: int
    tasks_done: int
    task_runs_total: int
    task_runs_success_30d: int
    ai_cost_cents_30d: int
