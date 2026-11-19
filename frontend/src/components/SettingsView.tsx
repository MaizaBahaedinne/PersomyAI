"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { AppSettings, DashboardSummary, Language, SessionInfo } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

type Tab = "profile" | "security" | "general" | "services" | "ai";
const TABS: Tab[] = ["profile", "security", "general", "services", "ai"];

export function SettingsView() {
  const { t } = useI18n();
  const [tab, setTab] = useState<Tab>("profile");
  return (
    <div>
      <PageHeader title={t("settings.title")} />
      <div role="tablist" aria-label={t("settings.title")} className="mb-6 flex flex-wrap gap-1 border-b border-ink-700">
        {TABS.map((id) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === id ? "border-accent text-accent" : "border-transparent text-slate-400 hover:text-white"}`}
            onClick={() => setTab(id)}
          >
            {t(`settings.tab.${id}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "profile" && <ProfileTab />}
        {tab === "security" && <SecurityTab />}
        {tab === "general" && <GeneralTab />}
        {tab === "services" && <ServicesTab />}
        {tab === "ai" && (
          <div className="card max-w-xl space-y-3">
            <h2 className="text-lg font-semibold text-white">{t("settings.ai.title")}</h2>
            <Badge tone="info">{t("dashboard.module_pending")}</Badge>
            <p className="text-sm text-slate-300">{t("settings.ai.pending")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ProfileTab() {
  const { t, setLocale } = useI18n();
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.display_name ?? "");
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? "fr");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setNotice(null);
    setError(null);
    try {
      await api("/auth/me", { method: "PATCH", body: { display_name: name, preferred_language: language } });
      setLocale(language);
      await refresh();
      setNotice(t("settings.saved"));
    } catch (err) {
      setError(t(errorKey(err)));
    }
  };

  if (!user) return null;
  return (
    <form onSubmit={submit} className="card max-w-xl space-y-4">
      <h2 className="text-lg font-semibold text-white">{t("settings.profile.title")}</h2>
      <div>
        <span className="label">{t("settings.profile.email")}</span>
        <p className="text-sm text-slate-300">{user.email}</p>
      </div>
      <div>
        <span className="label">{t("settings.profile.role")}</span>
        <Badge tone="info">{t(`role.${user.role}`)}</Badge>
      </div>
      <div>
        <label htmlFor="s-name" className="label">{t("users.display_name")}</label>
        <input id="s-name" required maxLength={120} className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div>
        <label htmlFor="s-lang" className="label">{t("users.language")}</label>
        <select id="s-lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
          <option value="fr">{t("lang.fr")}</option>
          <option value="en">{t("lang.en")}</option>
        </select>
      </div>
      {notice && <SuccessBanner message={notice} />}
      {error && <ErrorBanner message={error} />}
      <button type="submit" className="btn-primary">{t("common.save")}</button>
    </form>
  );
}

function SecurityTab() {
  const { t, locale } = useI18n();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessions = useAsync(() => api<SessionInfo[]>("/auth/sessions"), []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setNotice(null);
    setError(null);
    try {
      await api("/auth/change-password", { method: "POST", body: { current_password: current, new_password: next } });
      setCurrent("");
      setNext("");
      setNotice(t("settings.security.password_changed"));
      sessions.reload();
    } catch (err) {
      setError(t(errorKey(err)));
    }
  };

  const revoke = async (id: string) => {
    try {
      await api(`/auth/sessions/${id}`, { method: "DELETE" });
      sessions.reload();
    } catch (err) {
      setError(t(errorKey(err)));
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4">
        <h2 className="text-lg font-semibold text-white">{t("settings.security.password_title")}</h2>
        <div>
          <label htmlFor="cp" className="label">{t("settings.security.current_password")}</label>
          <input id="cp" type="password" required autoComplete="current-password" className="input" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div>
          <label htmlFor="np" className="label">{t("settings.security.new_password")}</label>
          <input id="np" type="password" required minLength={12} autoComplete="new-password" className="input" value={next} onChange={(e) => setNext(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t("users.password_hint")}</p>
        </div>
        {notice && <SuccessBanner message={notice} />}
        {error && <ErrorBanner message={error} />}
        <button type="submit" className="btn-primary">{t("common.save")}</button>
        <p className="text-xs text-slate-500">{t("settings.security.two_factor")}</p>
      </form>

      <section className="card">
        <h2 className="mb-3 text-lg font-semibold text-white">{t("settings.security.sessions_title")}</h2>
        {sessions.loading && !sessions.data ? (
          <Spinner />
        ) : sessions.error || !sessions.data ? (
          <ErrorBanner message={t("common.error")} onRetry={sessions.reload} />
        ) : sessions.data.length === 0 ? (
          <EmptyState message={t("common.none")} />
        ) : (
          <ul className="space-y-2">
            {sessions.data.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 rounded-lg bg-ink-800 px-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="truncate text-slate-200">{s.user_agent ?? "—"}</p>
                  <p className="text-xs text-slate-500">
                    {s.ip_address ?? "—"} · {t("settings.security.session_last_seen")} {formatDateTime(s.last_seen_at, locale)}
                  </p>
                </div>
                {s.current ? (
                  <Badge tone="ok">{t("settings.security.session_current")}</Badge>
                ) : (
                  <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => void revoke(s.id)}>
                    {t("settings.security.session_revoke")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function GeneralTab() {
  const { t } = useI18n();
  const { can } = useAuth();
  const canWrite = can("settings:write");
  const settings = useAsync(() => api<AppSettings>("/settings"), []);
  const [company, setCompany] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (settings.loading && !settings.data) return <Spinner />;
  if (settings.error || !settings.data) return <ErrorBanner message={t("common.error")} onRetry={settings.reload} />;

  const values = {
    company_name: company ?? settings.data.company_name,
    default_language: language ?? settings.data.default_language,
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setNotice(null);
    setError(null);
    try {
      await api("/settings", { method: "PUT", body: values });
      setNotice(t("settings.saved"));
      settings.reload();
    } catch (err) {
      setError(t(errorKey(err)));
    }
  };

  return (
    <form onSubmit={submit} className="card max-w-xl space-y-4">
      <h2 className="text-lg font-semibold text-white">{t("settings.general.title")}</h2>
      {!canWrite && <p className="text-sm text-slate-400">{t("settings.general.readonly")}</p>}
      <div>
        <label htmlFor="g-company" className="label">{t("settings.general.company")}</label>
        <input id="g-company" required maxLength={120} disabled={!canWrite} className="input" value={values.company_name} onChange={(e) => setCompany(e.target.value)} />
      </div>
      <div>
        <label htmlFor="g-lang" className="label">{t("settings.general.default_language")}</label>
        <select id="g-lang" disabled={!canWrite} className="input" value={values.default_language} onChange={(e) => setLanguage(e.target.value as Language)}>
          <option value="fr">{t("lang.fr")}</option>
          <option value="en">{t("lang.en")}</option>
        </select>
      </div>
      {notice && <SuccessBanner message={notice} />}
      {error && <ErrorBanner message={error} />}
      {canWrite && <button type="submit" className="btn-primary">{t("common.save")}</button>}
    </form>
  );
}

function ServicesTab() {
  const { t, has } = useI18n();
  const { data, loading, error, reload } = useAsync(() => api<DashboardSummary>("/dashboard/summary"), []);
  if (loading && !data) return <Spinner />;
  if (error || !data) return <ErrorBanner message={t("common.error")} onRetry={reload} />;
  return (
    <section className="card max-w-xl">
      <h2 className="mb-3 text-lg font-semibold text-white">{t("settings.services.title")}</h2>
      <ul className="space-y-2">
        {data.services.map((svc) => (
          <li key={svc.name} className="flex items-center justify-between rounded-lg bg-ink-800 px-3 py-2 text-sm">
            <span>{has(`dashboard.service.${svc.name}`) ? t(`dashboard.service.${svc.name}` as never) : svc.name}</span>
            <Badge tone={svc.status === "ok" ? "ok" : "danger"}>
              {svc.status === "ok" ? t("dashboard.service.ok") : t("dashboard.service.down")}
            </Badge>
          </li>
        ))}
      </ul>
    </section>
  );
}
