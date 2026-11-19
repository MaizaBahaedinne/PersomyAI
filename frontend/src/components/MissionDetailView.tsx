"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { Mission, MissionStatus, Page, TaskSummary } from "@/lib/types";
import { useI18n } from "@/i18n";
import { missionTone } from "@/components/MissionsView";
import { CreateTaskModal, TaskTable } from "@/components/TasksView";
import { Badge, ConfirmDialog, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const NEXT_STATUSES: Record<MissionStatus, MissionStatus[]> = {
  OPEN: ["DONE", "CANCELLED"],
  DONE: ["OPEN"],
  CANCELLED: ["OPEN"],
};

export function MissionDetailView({ id }: { id: string }) {
  const { t, label } = useI18n();
  const { can } = useAuth();
  const canWrite = can("orchestration:write");

  const missionState = useAsync(() => api<Mission>(`/missions/${id}`), [id]);
  const tasks = useAsync(() => api<Page<TaskSummary>>("/tasks", { params: { mission_id: id, limit: 100 } }), [id]);

  const [target, setTarget] = useState<MissionStatus | null>(null);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const mission = missionState.data;

  const changeStatus = async () => {
    if (!target) return;
    setBusy(true);
    setActionError(null);
    try {
      await api(`/missions/${id}`, { method: "PATCH", body: { status: target } });
      setTarget(null);
      setNotice(t("missions.updated"));
      missionState.reload();
    } catch (e) {
      setActionError(t(errorKey(e)));
    } finally {
      setBusy(false);
    }
  };

  if (missionState.loading && !mission) return <Spinner />;
  if (missionState.error || !mission) {
    return (
      <div className="space-y-4">
        <ErrorBanner message={t(errorKey(missionState.error))} onRetry={missionState.reload} />
        <Link href="/missions" className="btn-secondary">{t("missions.back")}</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={mission.title}
        subtitle={mission.description || undefined}
        actions={
          <div className="flex items-center gap-3">
            <Badge tone={missionTone(mission.status)}>{label("mission.status", mission.status)}</Badge>
            <Link href="/missions" className="btn-secondary">{t("missions.back")}</Link>
          </div>
        }
      />
      {notice && <SuccessBanner message={notice} />}

      {canWrite && (
        <section className="card flex flex-wrap gap-2" aria-label={t("missions.col_status")}>
          {NEXT_STATUSES[mission.status].map((s) => (
            <button
              key={s}
              type="button"
              className={s === "CANCELLED" ? "btn-danger" : "btn-secondary"}
              onClick={() => {
                setActionError(null);
                setTarget(s);
              }}
            >
              {label("mission.action", s)}
            </button>
          ))}
        </section>
      )}

      <EditForm mission={mission} canWrite={canWrite} onSaved={() => { setNotice(t("missions.updated")); missionState.reload(); }} />

      <section aria-label={t("missions.tasks")}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("missions.tasks")}</h2>
          {canWrite && mission.status === "OPEN" && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              {t("tasks.create")}
            </button>
          )}
        </div>
        {tasks.loading && !tasks.data ? (
          <Spinner />
        ) : tasks.error || !tasks.data ? (
          <ErrorBanner message={t("tasks.load_error")} onRetry={tasks.reload} />
        ) : tasks.data.items.length === 0 ? (
          <EmptyState message={t("tasks.empty")} />
        ) : (
          <div className="card overflow-x-auto p-0">
            <TaskTable items={tasks.data.items} showMission={false} />
          </div>
        )}
      </section>

      {creating && (
        <CreateTaskModal
          missionId={id}
          onClose={() => setCreating(false)}
          onDone={() => {
            setCreating(false);
            setNotice(t("tasks.created"));
            missionState.reload();
            tasks.reload();
          }}
        />
      )}
      {target && (
        <div>
          <ConfirmDialog
            title={label("mission.action", target)}
            message={t("missions.confirm_status", { name: mission.title, status: label("mission.status", target) })}
            danger={target === "CANCELLED"}
            busy={busy}
            onCancel={() => {
              setTarget(null);
              setActionError(null);
            }}
            onConfirm={changeStatus}
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

function EditForm({ mission, canWrite, onSaved }: { mission: Mission; canWrite: boolean; onSaved: () => void }) {
  const { t } = useI18n();
  const [title, setTitle] = useState(mission.title);
  const [description, setDescription] = useState(mission.description);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setTitle(mission.title);
    setDescription(mission.description);
  }, [mission]);

  if (!canWrite) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/missions/${mission.id}`, { method: "PATCH", body: { title, description } });
      onSaved();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-3" aria-label={t("tasks.details")}>
      <div>
        <label htmlFor="e-title" className="label">{t("missions.form.title")}</label>
        <input id="e-title" required maxLength={200} className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div>
        <label htmlFor="e-desc" className="label">{t("missions.form.description")}</label>
        <textarea id="e-desc" rows={3} maxLength={8000} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      {error && <ErrorBanner message={error} />}
      <div className="flex justify-end">
        <button type="submit" className="btn-primary" disabled={busy}>{t("common.save")}</button>
      </div>
    </form>
  );
}
