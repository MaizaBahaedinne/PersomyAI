"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import type { DepartmentSummary } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner } from "@/components/ui";

export function DepartmentsView() {
  const { t, label } = useI18n();
  const state = useAsync(() => api<{ items: DepartmentSummary[] }>("/departments/summary"), []);

  return (
    <div>
      <PageHeader title={t("departments.title")} subtitle={t("departments.subtitle")} />
      {state.loading && !state.data ? (
        <Spinner />
      ) : state.error || !state.data ? (
        <ErrorBanner message={t("departments.load_error")} onRetry={state.reload} />
      ) : state.data.items.length === 0 ? (
        <EmptyState message={t("departments.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("departments.col_name")}</th>
                <th className="th">{t("departments.col_agents_total")}</th>
                <th className="th">{t("departments.col_agents_active")}</th>
                <th className="th">{t("departments.col_agents_paused")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {state.data.items.map((d) => (
                <tr key={d.code}>
                  <td className="td font-medium">{label("department", d.code)}</td>
                  <td className="td"><Badge tone="info">{d.agents_total}</Badge></td>
                  <td className="td"><Badge tone="ok">{d.agents_active}</Badge></td>
                  <td className="td"><Badge tone="warn">{d.agents_paused}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
