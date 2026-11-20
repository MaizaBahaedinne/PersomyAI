"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { errorKey } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { FinanceSimulation, FinanceSummary } from "@/lib/types";
import { useI18n } from "@/i18n";
import { ErrorBanner, PageHeader, StatCard } from "@/components/ui";

function euros(cents: number): string {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(cents / 100);
}

export function FinanceView() {
  const { t } = useI18n();
  const state = useAsync(() => api<FinanceSummary>("/finance/summary"), []);

  const [form, setForm] = useState({
    monthly_revenue_cents: 3000000,
    gross_margin_percent: 45,
    ai_cost_cents_monthly: 20000,
    growth_percent: 8,
  });
  const [sim, setSim] = useState<FinanceSimulation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setSim(await api<FinanceSimulation>("/finance/simulate", { method: "POST", body: form }));
    } catch (err) {
      setError(t(errorKey(err)));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title={t("finance.title")} subtitle={t("finance.subtitle")} />

      {state.error ? (
        <ErrorBanner message={t("finance.load_error")} onRetry={state.reload} />
      ) : state.data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("finance.kpi.total_runs")} value={String(state.data.task_runs_total)} />
          <StatCard label={t("finance.kpi.total_cost")} value={euros(state.data.cost_cents_total)} />
          <StatCard label={t("finance.kpi.cost_30d")} value={euros(state.data.cost_cents_30d)} />
          <StatCard label={t("finance.kpi.avg_cost")} value={euros(Math.round(state.data.average_cost_cents))} />
        </div>
      ) : null}

      <form className="card space-y-4" onSubmit={submit}>
        <h2 className="text-lg font-semibold text-white">{t("finance.sim.title")}</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="label">
            {t("finance.sim.revenue")}
            <input
              className="input mt-1"
              type="number"
              min={0}
              value={form.monthly_revenue_cents}
              onChange={(e) => setForm((s) => ({ ...s, monthly_revenue_cents: Number(e.target.value || 0) }))}
            />
          </label>
          <label className="label">
            {t("finance.sim.margin_percent")}
            <input
              className="input mt-1"
              type="number"
              min={0}
              max={100}
              step="0.1"
              value={form.gross_margin_percent}
              onChange={(e) => setForm((s) => ({ ...s, gross_margin_percent: Number(e.target.value || 0) }))}
            />
          </label>
          <label className="label">
            {t("finance.sim.ai_cost")}
            <input
              className="input mt-1"
              type="number"
              min={0}
              value={form.ai_cost_cents_monthly}
              onChange={(e) => setForm((s) => ({ ...s, ai_cost_cents_monthly: Number(e.target.value || 0) }))}
            />
          </label>
          <label className="label">
            {t("finance.sim.growth")}
            <input
              className="input mt-1"
              type="number"
              min={-100}
              max={100}
              step="0.1"
              value={form.growth_percent}
              onChange={(e) => setForm((s) => ({ ...s, growth_percent: Number(e.target.value || 0) }))}
            />
          </label>
        </div>
        {error && <ErrorBanner message={error} />}
        <button type="submit" className="btn-primary">{t("finance.sim.run")}</button>
      </form>

      {sim && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("finance.sim.projected_revenue")} value={euros(sim.projected_revenue_cents)} />
          <StatCard label={t("finance.sim.projected_margin")} value={euros(sim.projected_margin_cents)} />
          <StatCard label={t("finance.sim.margin_after_ai")} value={euros(sim.margin_after_ai_cents)} />
          <StatCard label={t("finance.sim.ai_share")} value={`${sim.ai_cost_share_percent}%`} />
        </div>
      )}
    </div>
  );
}
