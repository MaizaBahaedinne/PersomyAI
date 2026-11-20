"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { TeamData } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, StatCard } from "@/components/ui";

export function TeamView() {
  const { t, locale, label } = useI18n();
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("");

  const data = useAsync(
    () =>
      api<TeamData>("/team", {
        params: {
          search,
          active: active === "" ? undefined : active === "1",
          limit: 100,
          offset: 0,
        },
      }),
    [search, active],
  );

  return (
    <div className="space-y-6">
      <PageHeader title={t("team.title")} subtitle={t("team.subtitle")} />

      {data.error ? (
        <ErrorBanner message={t("team.load_error")} onRetry={data.reload} />
      ) : data.loading && !data.data ? (
        <Spinner />
      ) : data.data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label={t("team.kpi.total")} value={String(data.data.summary.total)} />
            <StatCard label={t("team.kpi.active")} value={String(data.data.summary.active)} />
            <StatCard label={t("team.kpi.disabled")} value={String(data.data.summary.disabled)} />
            <StatCard label={t("team.kpi.super_admins")} value={String(data.data.summary.super_admins)} />
            <StatCard label={t("team.kpi.with_2fa")} value={String(data.data.summary.with_two_factor)} />
          </div>

          <div className="card space-y-4">
            <div className="flex flex-wrap gap-3">
              <input
                className="input max-w-xs"
                type="search"
                placeholder={t("team.search")}
                aria-label={t("team.search")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select className="input w-auto" value={active} onChange={(e) => setActive(e.target.value)}>
                <option value="">{t("team.filter_status")}: {t("common.all")}</option>
                <option value="1">{t("users.active")}</option>
                <option value="0">{t("users.disabled")}</option>
              </select>
            </div>

            {data.data.items.length === 0 ? (
              <EmptyState message={t("team.empty")} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-ink-700">
                    <tr>
                      <th className="th">{t("users.col_name")}</th>
                      <th className="th">{t("users.col_role")}</th>
                      <th className="th">{t("team.col_2fa")}</th>
                      <th className="th">{t("users.col_last_login")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-700">
                    {data.data.items.map((u) => (
                      <tr key={u.id}>
                        <td className="td">
                          <p className="font-medium">{u.display_name}</p>
                          <p className="text-xs text-slate-500">{u.email}</p>
                        </td>
                        <td className="td">
                          <Badge tone={u.is_active ? "ok" : "neutral"}>{label("role", u.role)}</Badge>
                        </td>
                        <td className="td">
                          <Badge tone={u.two_factor_enabled ? "ok" : "warn"}>
                            {u.two_factor_enabled ? t("team.2fa.on") : t("team.2fa.off")}
                          </Badge>
                        </td>
                        <td className="td text-slate-400">
                          {u.last_login_at ? formatDateTime(u.last_login_at, locale) : t("common.never")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
