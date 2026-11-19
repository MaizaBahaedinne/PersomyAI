"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { AgentCatalog, AgentSummary, Mission, Page, Priority, TaskStatus, TaskSummary } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, Modal, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

export const TASK_STATUSES: TaskStatus[] = [
  "OPEN",
  "AWAITING_APPROVAL",
  "APPROVED",
  "RUNNING",
  "DONE",
  "FAILED",
  "REJECTED",
  "CANCELLED",
];
const PRIORITIES: Priority[] = ["LOW", "NORMAL", "HIGH"];
const PAGE_SIZE = 25;

export function taskStatusTone(status: TaskStatus): "neutral" | "ok" | "warn" | "danger" | "info" {
  switch (status) {
    case "DONE":
      return "ok";
    case "AWAITING_APPROVAL":
    case "RUNNING":
      return "warn";
    case "FAILED":
    case "REJECTED":
      return "danger";
    case "APPROVED":
    case "OPEN":
      return "info";
    default:
      return "neutral";
  }
}

export function TaskTable({ items, showMission = true }: { items: TaskSummary[]; showMission?: boolean }) {
  const { t, label, locale } = useI18n();
  return (
    <table className="w-full">
      <thead className="border-b border-ink-700">
        <tr>
          <th className="th">{t("tasks.col_title")}</th>
          {showMission && <th className="th">{t("tasks.col_mission")}</th>}
          <th className="th">{t("tasks.col_agent")}</th>
          <th className="th">{t("tasks.col_status")}</th>
          <th className="th">{t("tasks.col_priority")}</th>
          <th className="th">{t("tasks.col_validation")}</th>
          <th className="th">{t("tasks.col_updated")}</th>
          <th className="th">{t("common.actions")}</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-ink-700">
        {items.map((task) => (
          <tr key={task.id}>
            <td className="td font-medium">{task.title}</td>
            {showMission && <td className="td text-slate-400">{task.mission_title ?? "—"}</td>}
            <td className="td text-slate-400">{task.agent_name ?? t("tasks.unassigned")}</td>
            <td className="td">
              <Badge tone={taskStatusTone(task.status)}>{label("task.status", task.status)}</Badge>
            </td>
            <td className="td text-slate-400">{label("priority", task.priority)}</td>
            <td className="td text-slate-400">
              {task.requires_approval === null
                ? "—"
                : task.requires_approval
                  ? t("tasks.validation_required")
                  : t("tasks.validation_none")}
            </td>
            <td className="td text-slate-400">{formatDateTime(task.updated_at, locale)}</td>
            <td className="td">
              <Link href={`/tasks/${task.id}`} className="btn-secondary px-2 py-1 text-xs">
                {t("tasks.view")}
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function CreateTaskModal({
  missionId,
  onClose,
  onDone,
}: {
  missionId?: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { t, label } = useI18n();
  const agents = useAsync(() => api<Page<AgentSummary>>("/agents", { params: { limit: 200 } }).catch(() => null), []);
  const catalog = useAsync(() => api<AgentCatalog>("/agents/catalog").catch(() => null), []);
  const missions = useAsync(
    () =>
      missionId
        ? Promise.resolve(null)
        : api<Page<Mission>>("/missions", { params: { status: "OPEN", limit: 200 } }).catch(() => null),
    [missionId],
  );

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("NORMAL");
  const [mission, setMission] = useState(missionId ?? "");
  const [agent, setAgent] = useState("");
  const [scope, setScope] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/tasks", {
        method: "POST",
        body: {
          title,
          description,
          priority,
          mission_id: mission || undefined,
          agent_id: agent || undefined,
          required_scope: scope || undefined,
        },
      });
      onDone();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("tasks.create")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="t-title" className="label">{t("tasks.form.title")}</label>
          <input id="t-title" required maxLength={200} className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label htmlFor="t-desc" className="label">{t("tasks.form.description")}</label>
          <textarea id="t-desc" rows={3} maxLength={8000} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="t-prio" className="label">{t("tasks.form.priority")}</label>
            <select id="t-prio" className="input" value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>{label("priority", p)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="t-mission" className="label">{t("tasks.form.mission")}</label>
            <select id="t-mission" className="input" disabled={!!missionId} value={mission} onChange={(e) => setMission(e.target.value)}>
              <option value="">{t("tasks.form.mission_none")}</option>
              {(missions.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.id}>{m.title}</option>
              ))}
              {missionId && <option value={missionId}>{missionId}</option>}
            </select>
          </div>
        </div>
        <div>
          <label htmlFor="t-agent" className="label">{t("tasks.form.agent")}</label>
          <select id="t-agent" className="input" value={agent} onChange={(e) => setAgent(e.target.value)}>
            <option value="">{t("tasks.form.agent_none")}</option>
            {(agents.data?.items ?? [])
              .filter((a) => a.status !== "DISABLED")
              .map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
          </select>
        </div>
        <div>
          <label htmlFor="t-scope" className="label">{t("tasks.form.scope")}</label>
          <select id="t-scope" className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="">{t("tasks.form.scope_none")}</option>
            {(catalog.data?.scopes ?? []).map((s) => (
              <option key={s.code} value={s.code}>
                {label("scope", s.code)}
                {s.critical ? ` (${t("agents.permissions_critical")})` : ""}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">{t("tasks.form.scope_hint")}</p>
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

export function TasksView() {
  const { t, label } = useI18n();
  const { can } = useAuth();
  const canWrite = can("orchestration:write");

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync(
    () => api<Page<TaskSummary>>("/tasks", { params: { search, status, limit: PAGE_SIZE, offset } }),
    [search, status, offset],
  );

  return (
    <div>
      <PageHeader
        title={t("tasks.title")}
        subtitle={t("tasks.subtitle")}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              {t("tasks.create")}
            </button>
          )
        }
      />
      {!canWrite && <p className="mb-4 text-sm text-slate-400">{t("tasks.readonly")}</p>}
      {notice && (
        <div className="mb-4">
          <SuccessBanner message={notice} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("tasks.search")}
          aria-label={t("tasks.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <select
          className="input w-auto"
          aria-label={t("tasks.filter_status")}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("tasks.filter_status")} : {t("common.all")}
          </option>
          {TASK_STATUSES.map((s) => (
            <option key={s} value={s}>{label("task.status", s)}</option>
          ))}
        </select>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorBanner message={t("tasks.load_error")} onRetry={reload} />
      ) : data.items.length === 0 ? (
        <EmptyState message={t("tasks.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <TaskTable items={data.items} />
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
        <CreateTaskModal
          onClose={() => setCreating(false)}
          onDone={() => {
            setCreating(false);
            setNotice(t("tasks.created"));
            reload();
          }}
        />
      )}
    </div>
  );
}
