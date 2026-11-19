"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { Agent, AgentCatalog, AgentStatus, AuditEvent, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { ActionLabel } from "@/components/DashboardView";
import { statusTone } from "@/components/AgentsView";
import { Badge, ConfirmDialog, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

/** Reflet des transitions autorisées côté serveur (le serveur reste l'autorité). */
const NEXT_STATUSES: Record<AgentStatus, AgentStatus[]> = {
  DRAFT: ["ACTIVE", "DISABLED"],
  ACTIVE: ["PAUSED", "DISABLED"],
  PAUSED: ["ACTIVE", "DISABLED"],
  ERROR: ["ACTIVE", "PAUSED", "DISABLED"],
  DISABLED: ["DRAFT"],
};

type Dialog = { kind: "status"; target: AgentStatus } | { kind: "revoke" } | { kind: "delete" } | null;

export function AgentDetailView({ id }: { id: string }) {
  const { t, label, locale } = useI18n();
  const { can } = useAuth();
  const router = useRouter();
  const canWrite = can("agents:write");
  const canGrant = can("agents:grant");
  const canDelete = can("agents:delete");

  const agentState = useAsync(() => api<Agent>(`/agents/${id}`), [id]);
  const catalog = useAsync(() => api<AgentCatalog>("/agents/catalog"), []);
  const history = useAsync(() => api<Page<AuditEvent>>(`/agents/${id}/history`, { params: { limit: 20 } }), [id]);

  const [dialog, setDialog] = useState<Dialog>(null);
  const [reason, setReason] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const agent = agentState.data;

  const refresh = () => {
    agentState.reload();
    history.reload();
  };

  const run = async (action: () => Promise<unknown>, success: string, after?: () => void) => {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      setDialog(null);
      setReason("");
      setNotice(success);
      if (after) after();
      else refresh();
    } catch (e) {
      setActionError(t(errorKey(e)));
    } finally {
      setBusy(false);
    }
  };

  if (agentState.loading && !agent) return <Spinner />;
  if (agentState.error || !agent) {
    return (
      <div className="space-y-4">
        <ErrorBanner message={t(errorKey(agentState.error))} onRetry={agentState.reload} />
        <Link href="/agents" className="btn-secondary">{t("agents.back")}</Link>
      </div>
    );
  }

  const closeDialog = () => {
    setDialog(null);
    setActionError(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={agent.name}
        subtitle={`${label("department", agent.department)} · ${agent.role}`}
        actions={
          <div className="flex items-center gap-3">
            <Badge tone={statusTone(agent.status)}>{label("agent.status", agent.status)}</Badge>
            <Link href="/agents" className="btn-secondary">{t("agents.back")}</Link>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {actionError && !dialog && <ErrorBanner message={actionError} />}
      {agent.access_revoked_at && (
        <ErrorBanner message={t("agents.revoked_notice", { date: formatDateTime(agent.access_revoked_at, locale) })} />
      )}

      <section className="card space-y-3" aria-label={t("agents.status_section")}>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.status_section")}</h2>
        <p className="text-xs text-slate-500">
          {t("agents.identity")} : <code className="text-slate-300">{agent.identity_key}</code>
        </p>
        {canWrite ? (
          <div className="flex flex-wrap gap-2">
            {NEXT_STATUSES[agent.status].map((target) => (
              <button
                key={target}
                type="button"
                className={target === "DISABLED" ? "btn-danger" : "btn-secondary"}
                onClick={() => setDialog({ kind: "status", target })}
              >
                {label("agent.action", target)}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">{t("agents.readonly")}</p>
        )}
      </section>

      <SettingsForm
        agent={agent}
        departments={catalog.data?.departments ?? []}
        canWrite={canWrite}
        canGrant={canGrant}
        onSaved={() => {
          setNotice(t("agents.updated"));
          refresh();
        }}
      />

      <AccessSection
        agent={agent}
        catalog={catalog.data}
        canGrant={canGrant}
        onSaved={() => {
          setNotice(t("agents.permissions_saved"));
          refresh();
        }}
      />

      {(canGrant || canDelete) && (
        <section className="card flex flex-wrap gap-2" aria-label={t("agents.settings")}>
          {canGrant && (
            <button type="button" className="btn-danger" onClick={() => setDialog({ kind: "revoke" })}>
              {t("agents.revoke")}
            </button>
          )}
          {canDelete && (
            <button type="button" className="btn-danger" onClick={() => setDialog({ kind: "delete" })}>
              {t("agents.delete")}
            </button>
          )}
        </section>
      )}

      <section className="card" aria-label={t("agents.history")}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.history")}</h2>
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
          <EmptyState message={t("agents.no_history")} />
        )}
      </section>

      {dialog && (
        <div>
          <ConfirmDialog
            title={
              dialog.kind === "status"
                ? label("agent.action", dialog.target)
                : dialog.kind === "revoke"
                  ? t("agents.revoke")
                  : t("agents.delete")
            }
            message={
              dialog.kind === "revoke"
                ? t("agents.revoke_confirm", { name: agent.name })
                : dialog.kind === "delete"
                  ? t("agents.delete_confirm", { name: agent.name })
                  : `${label("agent.status", agent.status)} → ${label("agent.status", dialog.target)}`
            }
            danger={dialog.kind !== "status" || dialog.target === "DISABLED"}
            busy={busy}
            onCancel={closeDialog}
            onConfirm={() => {
              if (dialog.kind === "status") {
                void run(
                  () =>
                    api(`/agents/${id}/status`, {
                      method: "POST",
                      body: { status: dialog.target, reason: reason.trim() || undefined },
                    }),
                  t("agents.status_changed"),
                );
              } else if (dialog.kind === "revoke") {
                void run(() => api(`/agents/${id}/revoke-access`, { method: "POST" }), t("agents.revoked"));
              } else {
                void run(() => api(`/agents/${id}`, { method: "DELETE" }), t("agents.deleted"), () =>
                  router.push("/agents"),
                );
              }
            }}
          />
          {dialog.kind === "status" && (
            <div className="fixed bottom-4 left-1/2 z-[60] w-full max-w-sm -translate-x-1/2 rounded-lg border border-ink-600 bg-ink-800 p-3">
              <label htmlFor="a-reason" className="label">{t("agents.status_reason")}</label>
              <input id="a-reason" maxLength={500} className="input" value={reason} onChange={(e) => setReason(e.target.value)} />
            </div>
          )}
          {actionError && (
            <div className="fixed left-1/2 top-4 z-[60] -translate-x-1/2">
              <ErrorBanner message={actionError} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SettingsForm({
  agent,
  departments,
  canWrite,
  canGrant,
  onSaved,
}: {
  agent: Agent;
  departments: string[];
  canWrite: boolean;
  canGrant: boolean;
  onSaved: () => void;
}) {
  const { t, label } = useI18n();
  const [name, setName] = useState(agent.name);
  const [description, setDescription] = useState(agent.description);
  const [department, setDepartment] = useState(agent.department);
  const [role, setRole] = useState(agent.role);
  const [mission, setMission] = useState(agent.mission);
  const [skills, setSkills] = useState(agent.skills.join(", "));
  const [maxActions, setMaxActions] = useState(String(agent.max_actions_per_day));
  const [budget, setBudget] = useState(String(agent.monthly_budget_cents));
  const [autonomy, setAutonomy] = useState(agent.autonomy_level);
  const [config, setConfig] = useState(JSON.stringify(agent.config, null, 2));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Resynchronise le formulaire quand l'agent est rechargé (changement de statut, etc.).
  useEffect(() => {
    setName(agent.name);
    setDescription(agent.description);
    setDepartment(agent.department);
    setRole(agent.role);
    setMission(agent.mission);
    setSkills(agent.skills.join(", "));
    setMaxActions(String(agent.max_actions_per_day));
    setBudget(String(agent.monthly_budget_cents));
    setAutonomy(agent.autonomy_level);
    setConfig(JSON.stringify(agent.config, null, 2));
  }, [agent]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(config || "{}");
    } catch {
      setError(t("agents.form.config_invalid"));
      return;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      setError(t("agents.form.config_invalid"));
      return;
    }
    const body: Record<string, unknown> = {
      name,
      description,
      department,
      role,
      mission,
      skills: skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      config: parsed,
      max_actions_per_day: Number(maxActions),
    };
    // Les champs réservés au SUPER_ADMIN ne sont envoyés que s'ils changent.
    if (autonomy !== agent.autonomy_level) body.autonomy_level = autonomy;
    if (Number(budget) !== agent.monthly_budget_cents) body.monthly_budget_cents = Number(budget);
    setBusy(true);
    try {
      await api(`/agents/${agent.id}`, { method: "PATCH", body });
      onSaved();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  const ro = !canWrite;
  return (
    <form onSubmit={submit} className="card space-y-3" aria-label={t("agents.settings")}>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.settings")}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="d-name" className="label">{t("agents.form.name")}</label>
          <input id="d-name" required maxLength={120} disabled={ro} className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label htmlFor="d-dept" className="label">{t("agents.form.department")}</label>
          <select id="d-dept" disabled={ro} className="input" value={department} onChange={(e) => setDepartment(e.target.value)}>
            {(departments.includes(department) ? departments : [department, ...departments]).map((d) => (
              <option key={d} value={d}>{label("department", d)}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="d-role" className="label">{t("agents.form.role")}</label>
          <input id="d-role" required maxLength={120} disabled={ro} className="input" value={role} onChange={(e) => setRole(e.target.value)} />
        </div>
        <div>
          <label htmlFor="d-skills" className="label">{t("agents.form.skills")}</label>
          <input id="d-skills" disabled={ro} className="input" value={skills} onChange={(e) => setSkills(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t("agents.form.skills_hint")}</p>
        </div>
      </div>
      <div>
        <label htmlFor="d-desc" className="label">{t("agents.form.description")}</label>
        <input id="d-desc" disabled={ro} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div>
        <label htmlFor="d-mission" className="label">{t("agents.form.mission")}</label>
        <textarea id="d-mission" rows={3} disabled={ro} className="input" value={mission} onChange={(e) => setMission(e.target.value)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="d-max" className="label">{t("agents.form.max_actions")}</label>
          <input id="d-max" type="number" min={0} disabled={ro} className="input" value={maxActions} onChange={(e) => setMaxActions(e.target.value)} />
        </div>
        <div>
          <label htmlFor="d-budget" className="label">{t("agents.form.budget")}</label>
          <input id="d-budget" type="number" min={0} disabled={ro} className="input" value={budget} onChange={(e) => setBudget(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t("agents.form.budget_hint")}</p>
        </div>
        <div>
          <label htmlFor="d-autonomy" className="label">{t("agents.form.autonomy")}</label>
          <select
            id="d-autonomy"
            disabled={ro}
            className="input"
            value={autonomy}
            onChange={(e) => setAutonomy(Number(e.target.value))}
          >
            {[1, 2, 3].map((n) => (
              <option key={n} value={n} disabled={n > agent.autonomy_level && !canGrant}>
                {label("agents.autonomy", String(n))}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">{t("agents.form.autonomy_hint")}</p>
        </div>
      </div>
      <div>
        <label htmlFor="d-config" className="label">{t("agents.form.config")}</label>
        <textarea id="d-config" rows={5} disabled={ro} spellCheck={false} className="input font-mono text-xs" value={config} onChange={(e) => setConfig(e.target.value)} />
        <p className="mt-1 text-xs text-slate-500">{t("agents.form.config_hint")}</p>
      </div>
      {error && <ErrorBanner message={error} />}
      {canWrite && (
        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={busy}>{t("common.save")}</button>
        </div>
      )}
    </form>
  );
}

function AccessSection({
  agent,
  catalog,
  canGrant,
  onSaved,
}: {
  agent: Agent;
  catalog: AgentCatalog | null;
  canGrant: boolean;
  onSaved: () => void;
}) {
  const { t, label } = useI18n();
  const [perms, setPerms] = useState<string[]>(agent.permissions);
  const [tools, setTools] = useState<string[]>(agent.tools);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setPerms(agent.permissions);
    setTools(agent.tools);
  }, [agent]);

  const toggle = (list: string[], set: (v: string[]) => void, code: string) =>
    set(list.includes(code) ? list.filter((c) => c !== code) : [...list, code]);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`/agents/${agent.id}/permissions`, { method: "PUT", body: { permissions: perms } });
      await api(`/agents/${agent.id}/tools`, { method: "PUT", body: { tools } });
      onSaved();
    } catch (e) {
      setError(t(errorKey(e)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card space-y-4" aria-label={t("agents.permissions")}>
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.permissions")}</h2>
        <p className="mt-1 text-xs text-slate-500">{t("agents.permissions_hint")}</p>
      </div>
      {canGrant ? (
        <>
          <fieldset className="grid gap-2 sm:grid-cols-2">
            <legend className="sr-only">{t("agents.permissions")}</legend>
            {(catalog?.scopes ?? []).map((s) => (
              <label key={s.code} className="flex items-center gap-2 text-sm text-slate-200">
                <input type="checkbox" checked={perms.includes(s.code)} onChange={() => toggle(perms, setPerms, s.code)} />
                <span>{label("scope", s.code)}</span>
                {s.critical && <Badge tone="warn">{t("agents.permissions_critical")}</Badge>}
              </label>
            ))}
          </fieldset>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.tools")}</h3>
          <fieldset className="grid gap-2 sm:grid-cols-2">
            <legend className="sr-only">{t("agents.tools")}</legend>
            {(catalog?.tools ?? []).map((tool) => (
              <label key={tool} className="flex items-center gap-2 text-sm text-slate-200">
                <input type="checkbox" checked={tools.includes(tool)} onChange={() => toggle(tools, setTools, tool)} />
                <span>{label("tool", tool)}</span>
              </label>
            ))}
          </fieldset>
          {error && <ErrorBanner message={error} />}
          <div className="flex justify-end">
            <button type="button" className="btn-primary" disabled={busy} onClick={save}>{t("common.save")}</button>
          </div>
        </>
      ) : (
        <>
          <ChipList items={agent.permissions.map((p) => label("scope", p))} />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{t("agents.tools")}</h3>
          <ChipList items={agent.tools.map((x) => label("tool", x))} />
          <p className="text-xs text-slate-500">{t("agents.permissions_readonly")}</p>
        </>
      )}
    </section>
  );
}

function ChipList({ items }: { items: string[] }) {
  const { t } = useI18n();
  if (items.length === 0) return <p className="text-sm text-slate-400">{t("agents.none")}</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((i) => (
        <Badge key={i}>{i}</Badge>
      ))}
    </div>
  );
}
