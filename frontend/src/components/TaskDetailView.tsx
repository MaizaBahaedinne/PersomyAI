"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type {
  AgentCatalog,
  AgentSummary,
  AuditEvent,
  Page,
  Priority,
  ProviderInfo,
  Task,
  TaskRun,
} from "@/lib/types";
import { useI18n } from "@/i18n";
import { ActionLabel } from "@/components/DashboardView";
import { taskStatusTone } from "@/components/TasksView";
import {
  Badge,
  ConfirmDialog,
  EmptyState,
  ErrorBanner,
  Modal,
  PageHeader,
  Spinner,
  SuccessBanner,
} from "@/components/ui";

type Dialog = "request" | "run" | "cancel" | "reopen" | "approve" | "reject" | null;

const PRIORITIES: Priority[] = ["LOW", "NORMAL", "HIGH"];
const LOCKED = ["RUNNING", "DONE", "CANCELLED"];
const STALE_RUNNING_MS = 15 * 60 * 1000;
const CANCELLABLE = ["OPEN", "AWAITING_APPROVAL", "APPROVED", "FAILED", "REJECTED"];

export function TaskDetailView({ id }: { id: string }) {
  const { t, label, locale } = useI18n();
  const { can } = useAuth();
  const canWrite = can("orchestration:write");
  const canApprove = can("orchestration:approve");
  const canRun = can("orchestration:run");

  const taskState = useAsync(() => api<Task>(`/tasks/${id}`), [id]);
  const runs = useAsync(() => api<TaskRun[]>(`/tasks/${id}/runs`), [id]);
  const history = useAsync(() => api<Page<AuditEvent>>(`/tasks/${id}/history`, { params: { limit: 20 } }), [id]);
  const provider = useAsync(() => api<ProviderInfo>("/tasks/provider").catch(() => null), []);
  const catalog = useAsync(() => api<AgentCatalog>("/agents/catalog").catch(() => null), []);
  const agents = useAsync(() => api<Page<AgentSummary>>("/agents", { params: { limit: 200 } }).catch(() => null), []);

  const [dialog, setDialog] = useState<Dialog>(null);
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const task = taskState.data;

  const refresh = () => {
    taskState.reload();
    runs.reload();
    history.reload();
  };

  const closeDialog = () => {
    setDialog(null);
    setText("");
    setActionError(null);
  };

  const act = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      setDialog(null);
      setText("");
      setNotice(success);
    } catch (e) {
      setActionError(t(errorKey(e)));
      setNotice(null);
    } finally {
      setBusy(false);
      refresh();
    }
  };

  const post = (action: string, body?: unknown) => api(`/tasks/${id}/${action}`, { method: "POST", body });

  const doRun = async (feedback?: string) => {
    setBusy(true);
    setActionError(null);
    try {
      const result = await api<{ task: Task; run: TaskRun }>(`/tasks/${id}/run`, {
        method: "POST",
        body: feedback?.trim() ? { feedback: feedback.trim() } : {},
      });
      setDialog(null);
      setText("");
      setNotice(
        result.run.status === "SUCCESS"
          ? t("tasks.n_run_done")
          : t("tasks.n_run_failed", { code: label("run.error", result.run.error_code ?? "unknown") }),
      );
    } catch (e) {
      setActionError(t(errorKey(e)));
      setNotice(null);
    } finally {
      setBusy(false);
      refresh();
    }
  };

  if (taskState.loading && !task) return <Spinner />;
  if (taskState.error || !task) {
    return (
      <div className="space-y-4">
        <ErrorBanner message={t(errorKey(taskState.error))} onRetry={taskState.reload} />
        <Link href="/tasks" className="btn-secondary">{t("tasks.back")}</Link>
      </div>
    );
  }

  const critical = !!task.required_scope && !!catalog.data?.scopes.find((s) => s.code === task.required_scope)?.critical;
  const runnable =
    task.status === "APPROVED" || (task.status === "OPEN" && !!task.agent_id && task.requires_approval === false);
  const canRequest = canWrite && task.status === "OPEN" && task.requires_approval === true;
  const canDecide = canApprove && task.status === "AWAITING_APPROVAL";
  const canCancel = canWrite && CANCELLABLE.includes(task.status);
  const stale = task.status === "RUNNING" && Date.now() - new Date(task.updated_at).getTime() > STALE_RUNNING_MS;
  const canReopen = canWrite && (task.status === "FAILED" || task.status === "REJECTED" || stale);
  const hasActions = canRequest || canDecide || (canRun && runnable) || canCancel || canReopen;

  return (
    <div className="space-y-6">
      <PageHeader
        title={task.title}
        subtitle={task.mission_title ?? undefined}
        actions={
          <div className="flex items-center gap-3">
            <Badge tone={taskStatusTone(task.status)}>{label("task.status", task.status)}</Badge>
            <Link href="/tasks" className="btn-secondary">{t("tasks.back")}</Link>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {actionError && !dialog && <ErrorBanner message={actionError} />}
      {provider.data &&
        (provider.data.configured ? (
          <p className="text-xs text-slate-500">{t("tasks.provider_ready", { name: provider.data.name })}</p>
        ) : (
          <ErrorBanner message={t("tasks.provider_missing")} />
        ))}

      <section className="card space-y-2" aria-label={t("tasks.approval_section")}>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("tasks.approval_section")}</h2>
        <p className="text-sm text-slate-300">
          {task.requires_approval === null
            ? t("tasks.approval_unknown")
            : task.requires_approval
              ? t("tasks.approval_needed")
              : t("tasks.approval_not_needed")}
        </p>
        {critical && <p className="text-xs text-amber-300">{t("tasks.four_eyes")}</p>}
        {task.decided_at && (
          <p className="text-sm text-slate-400">
            {t("tasks.decision", {
              who: task.decided_by_label ?? "—",
              date: formatDateTime(task.decided_at, locale),
            })}
            {task.decision_reason && <span> · {t("tasks.decision_reason", { reason: task.decision_reason })}</span>}
          </p>
        )}
        {hasActions && (
          <div className="flex flex-wrap gap-2 pt-2">
            {canRequest && (
              <button type="button" className="btn-secondary" onClick={() => setDialog("request")}>
                {label("task.action", "request_approval")}
              </button>
            )}
            {canDecide && (
              <>
                <button type="button" className="btn-primary" onClick={() => setDialog("approve")}>
                  {label("task.action", "approve")}
                </button>
                <button type="button" className="btn-danger" onClick={() => setDialog("reject")}>
                  {label("task.action", "reject")}
                </button>
              </>
            )}
            {canRun && runnable && (
              <button type="button" className="btn-primary" onClick={() => setDialog("run")}>
                {label("task.action", "run")}
              </button>
            )}
            {canReopen && (
              <button type="button" className="btn-secondary" onClick={() => setDialog("reopen")}>
                {label("task.action", "reopen")}
              </button>
            )}
            {canCancel && (
              <button type="button" className="btn-danger" onClick={() => setDialog("cancel")}>
                {label("task.action", "cancel")}
              </button>
            )}
          </div>
        )}
      </section>

      <DetailsForm
        task={task}
        agents={(agents.data?.items ?? []).filter((a) => a.status !== "DISABLED")}
        scopes={catalog.data?.scopes ?? []}
        editable={canWrite && !LOCKED.includes(task.status)}
        onSaved={() => {
          setNotice(t("tasks.updated"));
          refresh();
        }}
      />

      <section className="card" aria-label={t("tasks.runs")}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("tasks.runs")}</h2>
        {runs.data && runs.data.length > 0 ? (
          <ul className="space-y-3">
            {runs.data.map((r) => (
              <li key={r.id} className="rounded-lg bg-ink-800 px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    <Badge tone={r.status === "SUCCESS" ? "ok" : r.status === "FAILED" ? "danger" : "warn"}>
                      {label("run.status", r.status)}
                    </Badge>
                    <span className="text-slate-400">{r.provider}</span>
                    {r.error_code && <span className="text-red-300">{label("run.error", r.error_code)}</span>}
                  </span>
                  <span className="text-xs text-slate-500">{formatDateTime(r.started_at, locale)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {t("tasks.run_tokens", { tokens_in: r.tokens_in, tokens_out: r.tokens_out })} ·{" "}
                  {t("tasks.run_cost", { cents: r.cost_cents })}
                </p>
                {r.output && (
                  <pre aria-label={t("tasks.run_output")} className="mt-2 whitespace-pre-wrap break-words text-xs text-slate-300">
                    {r.output}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message={t("tasks.no_runs")} />
        )}
      </section>

      <section className="card" aria-label={t("tasks.history")}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("tasks.history")}</h2>
        {history.data && history.data.items.length > 0 ? (
          <ul className="space-y-2">
            {history.data.items.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-2 rounded-lg bg-ink-800 px-3 py-2 text-sm">
                <span>
                  <ActionLabel action={e.action} />
                  {e.actor_label && <span className="text-slate-500"> · {e.actor_label}</span>}
                </span>
                <span className="text-xs text-slate-500">{formatDateTime(e.created_at, locale)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message={t("tasks.no_history")} />
        )}
      </section>

      {(dialog === "approve" || dialog === "reject" || dialog === "run") && (
        <Modal title={label("task.action", dialog)} onClose={closeDialog}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (dialog === "run") {
                void doRun(text);
              } else if (dialog === "approve") {
                void act(() => post("approve", text.trim() ? { comment: text.trim() } : {}), t("tasks.n_approved"));
              } else {
                void act(() => post("reject", { reason: text.trim() }), t("tasks.n_rejected"));
              }
            }}
            className="space-y-3"
          >
            <div>
              <label htmlFor="decision-text" className="label">
                {dialog === "run"
                  ? t("tasks.run_feedback_label")
                  : dialog === "approve"
                    ? t("tasks.approve_comment")
                    : t("tasks.reject_reason")}
              </label>
              <textarea
                id="decision-text"
                rows={3}
                maxLength={dialog === "run" ? 2000 : 500}
                required={dialog === "reject"}
                className="input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={dialog === "run" ? t("tasks.run_feedback_placeholder") : undefined}
              />
            </div>
            {actionError && <ErrorBanner message={actionError} />}
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={closeDialog}>{t("common.cancel")}</button>
              <button
                type="submit"
                className={dialog === "reject" ? "btn-danger" : "btn-primary"}
                disabled={busy || (dialog === "reject" && !text.trim())}
              >
                {t("common.confirm")}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {(dialog === "request" || dialog === "cancel" || dialog === "reopen") && (
        <div>
          <ConfirmDialog
            title={label("task.action", dialog === "request" ? "request_approval" : dialog)}
            message={
              dialog === "request"
                ? t("tasks.confirm_request", { name: task.title })
                : dialog === "cancel"
                    ? t("tasks.confirm_cancel", { name: task.title })
                    : t("tasks.confirm_reopen")
            }
            danger={dialog === "cancel"}
            busy={busy}
            onCancel={closeDialog}
            onConfirm={() => {
              if (dialog === "request") void act(() => post("request-approval"), t("tasks.n_requested"));
              else if (dialog === "cancel") void act(() => post("cancel"), t("tasks.n_cancelled"));
              else void act(() => post("reopen"), t("tasks.n_reopened"));
            }}
          />
          {actionError && (
            <div className="fixed bottom-4 left-1/2 z-[60] -translate-x-1/2">
              <ErrorBanner message={actionError} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DetailsForm({
  task,
  agents,
  scopes,
  editable,
  onSaved,
}: {
  task: Task;
  agents: AgentSummary[];
  scopes: { code: string; critical: boolean }[];
  editable: boolean;
  onSaved: () => void;
}) {
  const { t, label } = useI18n();
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [priority, setPriority] = useState<Priority>(task.priority);
  const [agent, setAgent] = useState(task.agent_id ?? "");
  const [scope, setScope] = useState(task.required_scope ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setTitle(task.title);
    setDescription(task.description);
    setPriority(task.priority);
    setAgent(task.agent_id ?? "");
    setScope(task.required_scope ?? "");
  }, [task]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/tasks/${task.id}`, {
        method: "PATCH",
        body: { title, description, priority, agent_id: agent || null, required_scope: scope || null },
      });
      onSaved();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  const agentOptions = agents.some((a) => a.id === task.agent_id) || !task.agent_id
    ? agents
    : [...agents, { id: task.agent_id, name: task.agent_name ?? task.agent_id } as AgentSummary];

  return (
    <form onSubmit={submit} className="card space-y-3" aria-label={t("tasks.details")}>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("tasks.details")}</h2>
      <fieldset disabled={!editable} className="space-y-3">
        <div>
          <label htmlFor="d-title" className="label">{t("tasks.form.title")}</label>
          <input id="d-title" required maxLength={200} className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label htmlFor="d-desc" className="label">{t("tasks.form.description")}</label>
          <textarea id="d-desc" rows={4} maxLength={8000} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="d-prio" className="label">{t("tasks.form.priority")}</label>
            <select id="d-prio" className="input" value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>{label("priority", p)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="d-agent" className="label">{t("tasks.form.agent")}</label>
            <select id="d-agent" className="input" value={agent} onChange={(e) => setAgent(e.target.value)}>
              <option value="">{t("tasks.form.agent_none")}</option>
              {agentOptions.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="d-scope" className="label">{t("tasks.form.scope")}</label>
            <select id="d-scope" className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="">{t("tasks.form.scope_none")}</option>
              {scopes.map((s) => (
                <option key={s.code} value={s.code}>
                  {label("scope", s.code)}
                  {s.critical ? ` (${t("agents.permissions_critical")})` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>
      {editable && (task.status === "AWAITING_APPROVAL" || task.status === "APPROVED") && (
        <p className="text-xs text-amber-300">{t("tasks.edit_resets")}</p>
      )}
      {error && <ErrorBanner message={error} />}
      {editable && (
        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={busy}>{t("common.save")}</button>
        </div>
      )}
    </form>
  );
}
