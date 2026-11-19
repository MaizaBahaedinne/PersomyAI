"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { Mission, MissionStatus, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, Modal, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const PAGE_SIZE = 25;
const MISSION_STATUSES: MissionStatus[] = ["OPEN", "DONE", "CANCELLED"];

export function missionTone(status: MissionStatus): "neutral" | "ok" | "info" {
  return status === "DONE" ? "ok" : status === "OPEN" ? "info" : "neutral";
}

export function MissionsView() {
  const { t, label, locale } = useI18n();
  const { can } = useAuth();
  const canWrite = can("orchestration:write");

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync(
    () => api<Page<Mission>>("/missions", { params: { search, status, limit: PAGE_SIZE, offset } }),
    [search, status, offset],
  );

  return (
    <div>
      <PageHeader
        title={t("missions.title")}
        subtitle={t("missions.subtitle")}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              {t("missions.create")}
            </button>
          )
        }
      />
      {!canWrite && <p className="mb-4 text-sm text-slate-400">{t("missions.readonly")}</p>}
      {notice && (
        <div className="mb-4">
          <SuccessBanner message={notice} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("missions.search")}
          aria-label={t("missions.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <select
          className="input w-auto"
          aria-label={t("missions.filter_status")}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("missions.filter_status")} : {t("common.all")}
          </option>
          {MISSION_STATUSES.map((s) => (
            <option key={s} value={s}>{label("mission.status", s)}</option>
          ))}
        </select>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorBanner message={t("missions.load_error")} onRetry={reload} />
      ) : data.items.length === 0 ? (
        <EmptyState message={t("missions.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("missions.col_title")}</th>
                <th className="th">{t("missions.col_status")}</th>
                <th className="th">{t("missions.col_tasks")}</th>
                <th className="th">{t("missions.col_updated")}</th>
                <th className="th">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {data.items.map((m) => (
                <tr key={m.id}>
                  <td className="td font-medium">{m.title}</td>
                  <td className="td">
                    <Badge tone={missionTone(m.status)}>{label("mission.status", m.status)}</Badge>
                  </td>
                  <td className="td text-slate-400">{m.task_counts.total ?? 0}</td>
                  <td className="td text-slate-400">{formatDateTime(m.updated_at, locale)}</td>
                  <td className="td">
                    <Link href={`/missions/${m.id}`} className="btn-secondary px-2 py-1 text-xs">
                      {t("missions.view")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-ink-700 px-3 py-2 text-xs text-slate-400">
            <span>{t("common.total", { count: data.total })}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                {t("common.previous")}
              </button>
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                {t("common.next")}
              </button>
            </div>
          </div>
        </div>
      )}

      {creating && (
        <CreateMissionModal
          onClose={() => setCreating(false)}
          onDone={() => {
            setCreating(false);
            setNotice(t("missions.created"));
            reload();
          }}
        />
      )}
    </div>
  );
}

function CreateMissionModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/missions", { method: "POST", body: { title, description } });
      onDone();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("missions.create")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="m-title" className="label">{t("missions.form.title")}</label>
          <input id="m-title" required maxLength={200} className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label htmlFor="m-desc" className="label">{t("missions.form.description")}</label>
          <textarea id="m-desc" rows={4} maxLength={8000} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary" disabled={busy}>{t("common.create")}</button>
        </div>
      </form>
    </Modal>
  );
}
