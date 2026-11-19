"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { AgentCatalog, AgentStatus, AgentSummary, EmergencyState, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, ConfirmDialog, EmptyState, ErrorBanner, Modal, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const PAGE_SIZE = 25;

export function statusTone(status: AgentStatus): "neutral" | "ok" | "warn" | "danger" | "info" {
  switch (status) {
    case "ACTIVE":
      return "ok";
    case "PAUSED":
      return "warn";
    case "ERROR":
      return "danger";
    case "DISABLED":
      return "neutral";
    default:
      return "info";
  }
}

type Dialog = { kind: "create" } | { kind: "stop" } | { kind: "release" } | null;

export function AgentsView() {
  const { t, label, locale } = useI18n();
  const { can } = useAuth();
  const canWrite = can("agents:write");
  const canGrant = can("agents:grant");

  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const catalog = useAsync(() => api<AgentCatalog>("/agents/catalog"), []);
  const emergency = useAsync(() => api<EmergencyState>("/agents/emergency-stop"), []);
  const { data, loading, error, reload } = useAsync(
    () => api<Page<AgentSummary>>("/agents", { params: { search, department, status, limit: PAGE_SIZE, offset } }),
    [search, department, status, offset],
  );

  const stopActive = emergency.data?.active ?? false;

  const runEmergency = async (release: boolean) => {
    setBusy(true);
    setActionError(null);
    try {
      const result = await api<EmergencyState>("/agents/emergency-stop", { method: release ? "DELETE" : "POST" });
      setDialog(null);
      setNotice(
        release ? t("agents.emergency_released") : t("agents.emergency_done", { count: result.paused_agents }),
      );
      emergency.reload();
      reload();
    } catch (e) {
      setActionError(t(errorKey(e)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("agents.title")}
        subtitle={t("agents.subtitle")}
        actions={
          <div className="flex flex-wrap gap-2">
            {canWrite && !stopActive && (
              <button type="button" className="btn-danger" onClick={() => setDialog({ kind: "stop" })}>
                {t("agents.emergency_stop")}
              </button>
            )}
            {canGrant && stopActive && (
              <button type="button" className="btn-secondary" onClick={() => setDialog({ kind: "release" })}>
                {t("agents.emergency_release")}
              </button>
            )}
            {canWrite && (
              <button type="button" className="btn-primary" onClick={() => setDialog({ kind: "create" })}>
                {t("agents.create")}
              </button>
            )}
          </div>
        }
      />

      {stopActive && (
        <div className="mb-4">
          <ErrorBanner message={t("agents.emergency_banner")} />
        </div>
      )}
      {!canWrite && <p className="mb-4 text-sm text-slate-400">{t("agents.readonly")}</p>}
      {notice && (
        <div className="mb-4">
          <SuccessBanner message={notice} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("agents.search")}
          aria-label={t("agents.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <select
          className="input w-auto"
          aria-label={t("agents.filter_department")}
          value={department}
          onChange={(e) => {
            setDepartment(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("agents.filter_department")} : {t("common.all")}
          </option>
          {(catalog.data?.departments ?? []).map((d) => (
            <option key={d} value={d}>
              {label("department", d)}
            </option>
          ))}
        </select>
        <select
          className="input w-auto"
          aria-label={t("agents.filter_status")}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("agents.filter_status")} : {t("common.all")}
          </option>
          {(catalog.data?.statuses ?? []).map((s) => (
            <option key={s} value={s}>
              {label("agent.status", s)}
            </option>
          ))}
        </select>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorBanner message={t("agents.load_error")} onRetry={reload} />
      ) : data.items.length === 0 ? (
        <EmptyState message={t("agents.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("agents.col_name")}</th>
                <th className="th">{t("agents.col_department")}</th>
                <th className="th">{t("agents.col_role")}</th>
                <th className="th">{t("agents.col_status")}</th>
                <th className="th">{t("agents.col_autonomy")}</th>
                <th className="th">{t("agents.col_updated")}</th>
                <th className="th">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {data.items.map((a) => (
                <tr key={a.id}>
                  <td className="td font-medium">{a.name}</td>
                  <td className="td text-slate-400">{label("department", a.department)}</td>
                  <td className="td text-slate-400">{a.role}</td>
                  <td className="td">
                    <Badge tone={statusTone(a.status)}>{label("agent.status", a.status)}</Badge>
                  </td>
                  <td className="td text-slate-400">{a.autonomy_level}</td>
                  <td className="td text-slate-400">{formatDateTime(a.updated_at, locale)}</td>
                  <td className="td">
                    <Link href={`/agents/${a.id}`} className="btn-secondary px-2 py-1 text-xs">
                      {t("agents.view")}
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

      {dialog?.kind === "create" && (
        <CreateAgentModal
          departments={catalog.data?.departments ?? []}
          onClose={() => setDialog(null)}
          onDone={() => {
            setDialog(null);
            setNotice(t("agents.created"));
            reload();
          }}
        />
      )}
      {(dialog?.kind === "stop" || dialog?.kind === "release") && (
        <div>
          <ConfirmDialog
            title={dialog.kind === "stop" ? t("agents.emergency_stop") : t("agents.emergency_release")}
            message={dialog.kind === "stop" ? t("agents.emergency_confirm") : t("agents.emergency_release_confirm")}
            danger={dialog.kind === "stop"}
            busy={busy}
            onCancel={() => {
              setDialog(null);
              setActionError(null);
            }}
            onConfirm={() => runEmergency(dialog.kind === "release")}
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

function CreateAgentModal({ departments, onClose, onDone }: { departments: string[]; onClose: () => void; onDone: () => void }) {
  const { t, label } = useI18n();
  const [name, setName] = useState("");
  const [department, setDepartment] = useState(departments[0] ?? "");
  const [role, setRole] = useState("");
  const [mission, setMission] = useState("");
  const [skills, setSkills] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/agents", {
        method: "POST",
        body: {
          name,
          department,
          role,
          mission,
          skills: skills
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
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
    <Modal title={t("agents.create")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="a-name" className="label">{t("agents.form.name")}</label>
          <input id="a-name" required maxLength={120} className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="a-dept" className="label">{t("agents.form.department")}</label>
            <select id="a-dept" className="input" value={department} onChange={(e) => setDepartment(e.target.value)}>
              {departments.map((d) => (
                <option key={d} value={d}>{label("department", d)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="a-role" className="label">{t("agents.form.role")}</label>
            <input id="a-role" required maxLength={120} className="input" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
        </div>
        <div>
          <label htmlFor="a-mission" className="label">{t("agents.form.mission")}</label>
          <textarea id="a-mission" rows={3} maxLength={4000} className="input" value={mission} onChange={(e) => setMission(e.target.value)} />
        </div>
        <div>
          <label htmlFor="a-skills" className="label">{t("agents.form.skills")}</label>
          <input id="a-skills" className="input" value={skills} onChange={(e) => setSkills(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t("agents.form.skills_hint")}</p>
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary" disabled={busy || !department}>{t("common.create")}</button>
        </div>
      </form>
    </Modal>
  );
}
