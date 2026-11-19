"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { formatDateTime, formatTime } from "@/lib/errors";
import type { DashboardSummary } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, StatCard } from "@/components/ui";

export function ActionLabel({ action }: { action: string }) {
  const { t, has } = useI18n();
  const key = `action.${action}`;
  return <>{has(key) ? t(key) : action}</>;
}

export function DashboardView() {
  const { t, has, locale } = useI18n();
  const { data, loading, error, reload } = useAsync(() => api<DashboardSummary>("/dashboard/summary"), []);

  if (loading && !data) return <Spinner />;
  if (error || !data) return <ErrorBanner message={t("dashboard.load_error")} onRetry={reload} />;

  const s = data;
  return (
    <div className="space-y-6">
      <PageHeader
        title={t("dashboard.title")}
        subtitle={`${t("dashboard.subtitle", { company: s.company.name })} · ${t("dashboard.updated", {
          time: formatTime(s.generated_at, locale),
        })}`}
        actions={
          <button type="button" className="btn-secondary" onClick={reload}>
            {t("common.retry")}
          </button>
        }
      />

      <section aria-label={t("dashboard.security")} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label={t("dashboard.users_total")} value={s.users.total} />
        <StatCard label={t("dashboard.users_active")} value={s.users.active} />
        <StatCard label={t("dashboard.users_disabled")} value={s.users.disabled} />
        <StatCard label={t("dashboard.sessions_active")} value={s.sessions.active} />
        <StatCard label={t("dashboard.logins_ok")} value={s.security.logins_success_24h} />
        <StatCard label={t("dashboard.logins_failed")} value={s.security.logins_failed_24h} />
      </section>

      <section aria-label={t("nav.agents")}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("nav.agents")}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("dashboard.agents_active")} value={s.agents.active} />
          <StatCard label={t("dashboard.agents_paused")} value={s.agents.paused} />
          <StatCard label={t("dashboard.agents_error")} value={s.agents.error} />
          <StatCard label={t("dashboard.agents_total")} value={s.agents.total} />
        </div>
      </section>

      <section aria-label={t("dashboard.modules")}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("dashboard.modules")}</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {s.pending_modules.map((m) => (
            <div key={m} className="card">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {has(`nav.${m}`) ? t(`nav.${m}` as never) : m}
              </p>
              <div className="mt-2">
                <Badge tone="info">{t("dashboard.module_pending")}</Badge>
              </div>
              <p className="mt-2 text-xs text-slate-500">{t("dashboard.module_pending_hint")}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card" aria-label={t("dashboard.alerts")}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("dashboard.alerts")}</h2>
          {s.alerts.length === 0 ? (
            <EmptyState message={t("dashboard.no_alerts")} />
          ) : (
            <ul className="space-y-2">
              {s.alerts.map((a) => {
                const key = `alert.${a.code}`;
                return (
                  <li key={a.code} className="flex items-start gap-3 rounded-lg bg-ink-800 px-3 py-2 text-sm">
                    <Badge tone={a.severity === "warning" ? "warn" : "info"}>{a.severity}</Badge>
                    <span>{has(key) ? t(key, { count: a.count }) : a.code}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="card" aria-label={t("dashboard.services")}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("dashboard.services")}</h2>
          <ul className="space-y-2">
            {s.services.map((svc) => (
              <li key={svc.name} className="flex items-center justify-between rounded-lg bg-ink-800 px-3 py-2 text-sm">
                <span>{has(`dashboard.service.${svc.name}`) ? t(`dashboard.service.${svc.name}` as never) : svc.name}</span>
                <span className="flex items-center gap-3">
                  {svc.latency_ms !== null && <span className="text-xs text-slate-500">{svc.latency_ms} ms</span>}
                  <Badge tone={svc.status === "ok" ? "ok" : "danger"}>
                    {svc.status === "ok" ? t("dashboard.service.ok") : t("dashboard.service.down")}
                  </Badge>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card" aria-label={t("dashboard.recent_failures")}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("dashboard.recent_failures")}</h2>
          {s.security.recent_failures.length === 0 ? (
            <EmptyState message={t("dashboard.no_failures")} />
          ) : (
            <ul className="space-y-2">
              {s.security.recent_failures.map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-2 rounded-lg bg-ink-800 px-3 py-2 text-sm">
                  <span>
                    <ActionLabel action={e.action} />
                    {e.actor_label && <span className="text-slate-500"> · {e.actor_label}</span>}
                  </span>
                  <span className="text-xs text-slate-500">{formatDateTime(e.created_at, locale)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card" aria-label={t("dashboard.activity")}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("dashboard.activity")}</h2>
          {s.recent_activity.length === 0 ? (
            <EmptyState message={t("dashboard.no_activity")} />
          ) : (
            <ul className="space-y-2">
              {s.recent_activity.map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-2 rounded-lg bg-ink-800 px-3 py-2 text-sm">
                  <span>
                    <ActionLabel action={e.action} />
                    {e.actor_label && <span className="text-slate-500"> · {e.actor_label}</span>}
                  </span>
                  <span className="text-xs text-slate-500">{formatDateTime(e.created_at, locale)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
