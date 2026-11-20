"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { AppSettings, DashboardSummary, Language, ProviderInfo, SessionInfo } from "@/lib/types";
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
        {tab === "ai" && <AiTab />}
      </div>
    </div>
  );
}

function AiTab() {
  const { t } = useI18n();
  const provider = useAsync(() => api<ProviderInfo>("/tasks/provider"), []);

  return (
    <div className="card max-w-xl space-y-3">
      <h2 className="text-lg font-semibold text-white">{t("settings.ai.title")}</h2>
      {provider.loading && !provider.data ? (
        <Spinner />
      ) : provider.error || !provider.data ? (
        <ErrorBanner message={t("common.error")} onRetry={provider.reload} />
      ) : provider.data.configured ? (
        <>
          <Badge tone="ok">{t("common.confirm")}</Badge>
          <p className="text-sm text-slate-300">{t("tasks.provider_ready", { name: provider.data.name })}</p>
        </>
      ) : (
        <>
          <Badge tone="info">{t("dashboard.module_pending")}</Badge>
          <p className="text-sm text-slate-300">{t("tasks.provider_missing")}</p>
        </>
      )}
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
      </form>

      <TwoFactorCard />

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

interface TwoFactorState {
  enabled: boolean;
  available: boolean;
  recovery_codes_left: number;
}

type TwoFactorMode = "idle" | "setup" | "disable" | "regenerate";

function TwoFactorCard() {
  const { t } = useI18n();
  const status = useAsync(() => api<TwoFactorState>("/auth/2fa"), []);
  const [mode, setMode] = useState<TwoFactorMode>("idle");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string; qr_svg_data_uri: string } | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setMode("idle");
    setPassword("");
    setCode("");
    setSetup(null);
    setError(null);
  };

  const run = async (action: () => Promise<void>) => {
    setError(null);
    setBusy(true);
    try {
      await action();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  const start = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      setSetup(
        await api<{ secret: string; otpauth_uri: string; qr_svg_data_uri: string }>("/auth/2fa/setup", {
          method: "POST",
          body: { password },
        }),
      );
      setPassword("");
    });
  };

  const confirm = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const res = await api<{ recovery_codes: string[] }>("/auth/2fa/enable", { method: "POST", body: { code } });
      reset();
      setCodes(res.recovery_codes);
      status.reload();
    });
  };

  const disable = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await api("/auth/2fa/disable", { method: "POST", body: { password, code } });
      reset();
      status.reload();
    });
  };

  const regenerate = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const res = await api<{ recovery_codes: string[] }>("/auth/2fa/recovery-codes", { method: "POST", body: { password, code } });
      reset();
      setCodes(res.recovery_codes);
      status.reload();
    });
  };

  const passwordField = (
    <div>
      <label htmlFor="tfa-pw" className="label">{t("settings.security.2fa.password")}</label>
      <input id="tfa-pw" type="password" required autoComplete="current-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
    </div>
  );
  const codeField = (
    <div>
      <label htmlFor="tfa-code" className="label">{t("settings.security.2fa.code")}</label>
      <input id="tfa-code" type="text" required autoComplete="one-time-code" className="input" value={code} onChange={(e) => setCode(e.target.value)} />
    </div>
  );

  return (
    <section className="card space-y-4">
      <h2 className="text-lg font-semibold text-white">{t("settings.security.2fa.title")}</h2>
      {status.loading && !status.data ? (
        <Spinner />
      ) : status.error || !status.data ? (
        <ErrorBanner message={t("common.error")} onRetry={status.reload} />
      ) : (
        <>
          <p className="text-sm text-slate-400">{t("settings.security.2fa.intro")}</p>
          <div className="flex items-center gap-3">
            <Badge tone={status.data.enabled ? "ok" : "neutral"}>
              {t(status.data.enabled ? "settings.security.2fa.enabled" : "settings.security.2fa.disabled")}
            </Badge>
            {status.data.enabled && (
              <span className="text-xs text-slate-500">
                {t("settings.security.2fa.codes_left", { count: status.data.recovery_codes_left })}
              </span>
            )}
          </div>

          {!status.data.available && !status.data.enabled && (
            <p role="note" className="text-sm text-amber-200">{t("settings.security.2fa.unavailable")}</p>
          )}

          {codes && (
            <div role="group" aria-label={t("settings.security.2fa.codes_title")} className="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
              <p className="text-sm font-medium text-amber-100">{t("settings.security.2fa.codes_title")}</p>
              <p className="text-xs text-amber-200">{t("settings.security.2fa.codes_warning")}</p>
              <ul className="grid grid-cols-2 gap-1 font-mono text-sm text-white">
                {codes.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
              <button type="button" className="btn-secondary" onClick={() => setCodes(null)}>
                {t("settings.security.2fa.codes_done")}
              </button>
            </div>
          )}

          {error && <ErrorBanner message={error} />}

          {mode === "idle" && !codes && (
            <div className="flex flex-wrap gap-2">
              {!status.data.enabled && status.data.available && (
                <button type="button" className="btn-primary" onClick={() => setMode("setup")}>
                  {t("settings.security.2fa.start")}
                </button>
              )}
              {status.data.enabled && (
                <>
                  <button type="button" className="btn-secondary" onClick={() => setMode("regenerate")}>
                    {t("settings.security.2fa.regenerate")}
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => setMode("disable")}>
                    {t("settings.security.2fa.disable")}
                  </button>
                </>
              )}
            </div>
          )}

          {mode === "setup" && !setup && (
            <form onSubmit={start} className="space-y-3">
              {passwordField}
              <div className="flex gap-2">
                <button type="submit" className="btn-primary" disabled={busy}>{t("settings.security.2fa.start")}</button>
                <button type="button" className="btn-secondary" onClick={reset}>{t("common.cancel")}</button>
              </div>
            </form>
          )}

          {mode === "setup" && setup && (
            <form onSubmit={confirm} className="space-y-3">
              <p className="text-xs text-slate-400">{t("settings.security.2fa.setup_hint")}</p>
              <div className="flex justify-center rounded border border-slate-700/60 bg-ink-800/60 p-3">
                <img src={setup.qr_svg_data_uri} alt={t("settings.security.2fa.qr_alt")} className="h-40 w-40" />
              </div>
              <div>
                <p className="label">{t("settings.security.2fa.secret_label")}</p>
                <code className="block break-all rounded bg-ink-800 px-3 py-2 text-sm text-white">{setup.secret}</code>
              </div>
              <div>
                <p className="label">{t("settings.security.2fa.uri_label")}</p>
                <code className="block break-all rounded bg-ink-800 px-3 py-2 text-xs text-slate-300">{setup.otpauth_uri}</code>
              </div>
              {codeField}
              <div className="flex gap-2">
                <button type="submit" className="btn-primary" disabled={busy}>{t("settings.security.2fa.confirm")}</button>
                <button type="button" className="btn-secondary" onClick={reset}>{t("common.cancel")}</button>
              </div>
            </form>
          )}

          {(mode === "disable" || mode === "regenerate") && (
            <form onSubmit={mode === "disable" ? disable : regenerate} className="space-y-3">
              {passwordField}
              {codeField}
              <div className="flex gap-2">
                <button type="submit" className="btn-primary" disabled={busy}>
                  {t(mode === "disable" ? "settings.security.2fa.disable" : "settings.security.2fa.regenerate")}
                </button>
                <button type="button" className="btn-secondary" onClick={reset}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
        </>
      )}
    </section>
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
