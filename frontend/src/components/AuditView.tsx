"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { AuditEvent, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner } from "@/components/ui";
import { ActionLabel } from "@/components/DashboardView";

const PAGE_SIZE = 50;

export function AuditView() {
  const { t, locale } = useI18n();
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, loading, error, reload } = useAsync(
    () => api<Page<AuditEvent>>("/audit", { params: { action, actor, status, limit: PAGE_SIZE, offset } }),
    [action, actor, status, offset],
  );

  return (
    <div>
      <PageHeader title={t("audit.title")} subtitle={t("audit.subtitle")} />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className="input max-w-xs" placeholder={t("audit.filter_action")} aria-label={t("audit.filter_action")} value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }} />
        <input className="input max-w-xs" placeholder={t("audit.filter_actor")} aria-label={t("audit.filter_actor")} value={actor} onChange={(e) => { setActor(e.target.value); setOffset(0); }} />
        <select className="input w-auto" aria-label={t("audit.filter_status")} value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
          <option value="">{t("audit.filter_status")} : {t("common.all")}</option>
          <option value="success">{t("audit.success")}</option>
          <option value="failure">{t("audit.failure")}</option>
        </select>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorBanner message={t("audit.load_error")} onRetry={reload} />
      ) : data.items.length === 0 ? (
        <EmptyState message={t("audit.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("audit.col_date")}</th>
                <th className="th">{t("audit.col_actor")}</th>
                <th className="th">{t("audit.col_action")}</th>
                <th className="th">{t("audit.col_target")}</th>
                <th className="th">{t("audit.col_status")}</th>
                <th className="th">{t("audit.col_ip")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {data.items.map((e) => (
                <tr key={e.id}>
                  <td className="td whitespace-nowrap text-slate-400">{formatDateTime(e.created_at, locale)}</td>
                  <td className="td">{e.actor_label ?? "—"}</td>
                  <td className="td"><ActionLabel action={e.action} /></td>
                  <td className="td text-slate-400">{e.target_type ?? "—"}</td>
                  <td className="td"><Badge tone={e.status === "success" ? "ok" : "danger"}>{e.status === "success" ? t("audit.success") : t("audit.failure")}</Badge></td>
                  <td className="td text-slate-400">{e.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-ink-700 px-3 py-2 text-xs text-slate-400">
            <span>{t("common.total", { count: data.total })}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>{t("common.previous")}</button>
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>{t("common.next")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
