"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useI18n } from "@/i18n";
import { ErrorBanner, PageHeader, Spinner, StatCard } from "@/components/ui";

interface AnalyticsSummary {
  users_total: number;
  users_active: number;
  users_with_2fa: number;
  agents_total: number;
  automations_total: number;
  automations_active: number;
  companies_total: number;
  contacts_total: number;
  tasks_total: number;
  tasks_open: number;
  tasks_done: number;
  task_runs_total: number;
  task_runs_success_30d: number;
  ai_cost_cents_30d: number;
}

function euros(cents: number): string {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(cents / 100);
}

export function AnalyticsView() {
  const { t } = useI18n();
  const state = useAsync(() => api<AnalyticsSummary>("/analytics/summary"), []);

  if (state.loading && !state.data) return <Spinner />;
  if (state.error || !state.data) return <ErrorBanner message={t("analytics.load_error")} onRetry={state.reload} />;

  const a = state.data;
  return (
    <div className="space-y-6">
      <PageHeader title={t("analytics.title")} subtitle={t("analytics.subtitle")} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("analytics.kpi.users_total")} value={String(a.users_total)} />
        <StatCard label={t("analytics.kpi.users_active")} value={String(a.users_active)} />
        <StatCard label={t("analytics.kpi.users_2fa")} value={String(a.users_with_2fa)} />
        <StatCard label={t("analytics.kpi.agents_total")} value={String(a.agents_total)} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("analytics.kpi.companies_total")} value={String(a.companies_total)} />
        <StatCard label={t("analytics.kpi.contacts_total")} value={String(a.contacts_total)} />
        <StatCard label={t("analytics.kpi.automations_total")} value={String(a.automations_total)} />
        <StatCard label={t("analytics.kpi.automations_active")} value={String(a.automations_active)} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("analytics.kpi.tasks_total")} value={String(a.tasks_total)} />
        <StatCard label={t("analytics.kpi.tasks_open")} value={String(a.tasks_open)} />
        <StatCard label={t("analytics.kpi.tasks_done")} value={String(a.tasks_done)} />
        <StatCard label={t("analytics.kpi.runs_total")} value={String(a.task_runs_total)} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label={t("analytics.kpi.runs_success_30d")} value={String(a.task_runs_success_30d)} />
        <StatCard label={t("analytics.kpi.ai_cost_30d")} value={euros(a.ai_cost_cents_30d)} />
      </div>
    </div>
  );
}
