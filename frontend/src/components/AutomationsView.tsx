"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { Automation, AutomationStatus, AutomationTriggerType, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, Modal, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const PAGE_SIZE = 25;
const STATUSES: AutomationStatus[] = ["DRAFT", "ACTIVE", "PAUSED"];
const TRIGGERS: AutomationTriggerType[] = ["TASK_STATUS_CHANGED", "SCHEDULE"];

function statusTone(status: AutomationStatus): "neutral" | "ok" | "warn" {
  return status === "ACTIVE" ? "ok" : status === "PAUSED" ? "warn" : "neutral";
}

export function AutomationsView() {
  const { t, locale, label } = useI18n();
  const { can } = useAuth();
  const canWrite = can("automations:write");

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [triggerType, setTriggerType] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const list = useAsync(
    () => api<Page<Automation>>("/automations", { params: { search, status, trigger_type: triggerType, limit: PAGE_SIZE, offset } }),
    [search, status, triggerType, offset],
  );

  return (
    <div>
      <PageHeader
        title={t("automations.title")}
        subtitle={t("automations.subtitle")}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              {t("automations.create")}
            </button>
          )
        }
      />

      {!canWrite && <p className="mb-4 text-sm text-slate-400">{t("automations.readonly")}</p>}
      {notice && (
        <div className="mb-4">
          <SuccessBanner message={notice} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("automations.search")}
          aria-label={t("automations.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <select
          className="input w-auto"
          aria-label={t("automations.filter_status")}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("automations.filter_status")} : {t("common.all")}
          </option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{label("automation.status", s)}</option>
          ))}
        </select>
        <select
          className="input w-auto"
          aria-label={t("automations.filter_trigger")}
          value={triggerType}
          onChange={(e) => {
            setTriggerType(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">
            {t("automations.filter_trigger")} : {t("common.all")}
          </option>
          {TRIGGERS.map((v) => (
            <option key={v} value={v}>{label("automation.trigger", v)}</option>
          ))}
        </select>
      </div>

      {list.loading && !list.data ? (
        <Spinner />
      ) : list.error || !list.data ? (
        <ErrorBanner message={t("automations.load_error")} onRetry={list.reload} />
      ) : list.data.items.length === 0 ? (
        <EmptyState message={t("automations.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("automations.col_name")}</th>
                <th className="th">{t("automations.col_trigger")}</th>
                <th className="th">{t("automations.col_status")}</th>
                <th className="th">{t("automations.col_updated")}</th>
                <th className="th">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {list.data.items.map((row) => (
                <tr key={row.id}>
                  <td className="td font-medium">{row.name}</td>
                  <td className="td text-slate-300">{label("automation.trigger", row.trigger_type)}</td>
                  <td className="td">
                    <Badge tone={statusTone(row.status)}>{label("automation.status", row.status)}</Badge>
                  </td>
                  <td className="td text-slate-400">{formatDateTime(row.updated_at, locale)}</td>
                  <td className="td">
                    {canWrite ? (
                      <StatusButtons
                        row={row}
                        onChanged={() => {
                          setNotice(t("automations.status_updated"));
                          list.reload();
                        }}
                      />
                    ) : (
                      <span className="text-xs text-slate-500">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center justify-between border-t border-ink-700 px-4 py-3 text-sm text-slate-400">
            <span>{t("common.total", { count: list.data.total })}</span>
            <div className="space-x-2">
              <button
                type="button"
                className="btn-secondary px-2 py-1 text-xs"
                disabled={offset <= 0}
                onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}
              >
                {t("common.previous")}
              </button>
              <button
                type="button"
                className="btn-secondary px-2 py-1 text-xs"
                disabled={offset + PAGE_SIZE >= list.data.total}
                onClick={() => setOffset((v) => v + PAGE_SIZE)}
              >
                {t("common.next")}
              </button>
            </div>
          </div>
        </div>
      )}

      {creating && (
        <CreateAutomationModal
          onClose={() => setCreating(false)}
          onCreated={(name) => {
            setNotice(t("automations.created", { name }));
            setCreating(false);
            list.reload();
          }}
        />
      )}
    </div>
  );
}

function StatusButtons({ row, onChanged }: { row: Automation; onChanged: () => void }) {
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);

  async function setStatus(status: AutomationStatus) {
    setError(null);
    try {
      await api(`/automations/${row.id}/status`, { method: "POST", body: { status } });
      onChanged();
    } catch (err) {
      setError(t(errorKey(err)));
    }
  }

  return (
    <div className="space-y-1">
      <div className="flex gap-1">
        {row.status !== "ACTIVE" && (
          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => void setStatus("ACTIVE")}>
            {t("automations.activate")}
          </button>
        )}
        {row.status === "ACTIVE" && (
          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => void setStatus("PAUSED")}>
            {t("automations.pause")}
          </button>
        )}
        {row.status !== "DRAFT" && (
          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => void setStatus("DRAFT")}>
            {t("automations.to_draft")}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-300">{error}</p>}
    </div>
  );
}

function CreateAutomationModal({ onClose, onCreated }: { onClose: () => void; onCreated: (name: string) => void }) {
  const { t, label } = useI18n();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<AutomationTriggerType>("TASK_STATUS_CHANGED");
  const [cooldownSeconds, setCooldownSeconds] = useState(60);
  const [antiLoopKey, setAntiLoopKey] = useState("task-status-change");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api<Automation>("/automations", {
        method: "POST",
        body: {
          name,
          description,
          trigger_type: triggerType,
          trigger_config: triggerType === "TASK_STATUS_CHANGED" ? { from: "OPEN", to: "DONE" } : { cron: "0 * * * *" },
          conditions: [{ type: "task.required_scope", equals: "crm:read" }],
          actions: [{ type: "notify.audit", channel: "internal" }],
          anti_loop_key: antiLoopKey || null,
          cooldown_seconds: cooldownSeconds,
        },
      });
      onCreated(name);
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("automations.create")} onClose={onClose}>
      <form className="space-y-3" onSubmit={submit}>
        <div>
          <label htmlFor="auto-name" className="label">{t("automations.form.name")}</label>
          <input id="auto-name" className="input" required maxLength={160} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label htmlFor="auto-description" className="label">{t("automations.form.description")}</label>
          <textarea id="auto-description" className="input min-h-24" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label htmlFor="auto-trigger" className="label">{t("automations.form.trigger")}</label>
          <select id="auto-trigger" className="input" value={triggerType} onChange={(e) => setTriggerType(e.target.value as AutomationTriggerType)}>
            {TRIGGERS.map((v) => (
              <option key={v} value={v}>{label("automation.trigger", v)}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="auto-key" className="label">{t("automations.form.loop_key")}</label>
          <input id="auto-key" className="input" maxLength={120} value={antiLoopKey} onChange={(e) => setAntiLoopKey(e.target.value)} />
        </div>
        <div>
          <label htmlFor="auto-cooldown" className="label">{t("automations.form.cooldown")}</label>
          <input
            id="auto-cooldown"
            type="number"
            min={0}
            max={86400}
            className="input"
            value={cooldownSeconds}
            onChange={(e) => setCooldownSeconds(Number(e.target.value || 0))}
          />
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? t("common.loading") : t("common.create")}</button>
        </div>
      </form>
    </Modal>
  );
}
