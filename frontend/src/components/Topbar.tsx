"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n, LOCALES, type Locale } from "@/i18n";
import type { DashboardSummary } from "@/lib/types";

export function LanguageSwitch({ persist = false }: { persist?: boolean }) {
  const { locale, setLocale, t } = useI18n();
  const { status, refresh } = useAuth();

  const change = async (next: Locale) => {
    setLocale(next);
    if (persist && status === "authenticated") {
      try {
        await api("/auth/me", { method: "PATCH", body: { preferred_language: next } });
        await refresh();
      } catch {
        /* la langue reste appliquée localement */
      }
    }
  };

  return (
    <label className="flex items-center gap-2 text-xs text-slate-400">
      <span className="sr-only">{t("topbar.language")}</span>
      <select
        className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1 text-xs text-slate-200 focus:border-accent focus:outline-none"
        value={locale}
        onChange={(e) => change(e.target.value as Locale)}
        aria-label={t("topbar.language")}
      >
        {LOCALES.map((l) => (
          <option key={l} value={l}>
            {t(`lang.${l}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

function AlertsBell() {
  const { t, has } = useI18n();
  const [alerts, setAlerts] = useState<DashboardSummary["alerts"]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api<DashboardSummary>("/dashboard/summary")
        .then((s) => !cancelled && setAlerts(s.alerts))
        .catch(() => undefined);
    load();
    const id = setInterval(load, 60_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="btn-secondary relative"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={t("topbar.notifications")}
        onClick={() => setOpen((o) => !o)}
      >
        <span aria-hidden>🔔</span>
        {alerts.length > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-ink-950">
            {alerts.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-ink-600 bg-ink-900 p-3 shadow-2xl">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{t("topbar.notifications")}</p>
          {alerts.length === 0 ? (
            <p className="text-sm text-slate-400">{t("topbar.no_notifications")}</p>
          ) : (
            <ul className="space-y-2">
              {alerts.map((a) => {
                const key = `alert.${a.code}`;
                return (
                  <li key={a.code} className="rounded-lg bg-ink-800 px-3 py-2 text-sm text-slate-200">
                    {has(key) ? t(key, { count: a.count }) : a.code}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { t } = useI18n();
  const { user, logout } = useAuth();
  return (
    <header className="flex h-14 items-center justify-between gap-3 border-b border-ink-700 bg-ink-900/70 px-4 backdrop-blur">
      <button type="button" className="btn-secondary lg:hidden" onClick={onMenu} aria-label={t("topbar.menu")}>
        ☰
      </button>
      <div className="hidden lg:block" />
      <div className="flex items-center gap-3">
        <LanguageSwitch persist />
        <AlertsBell />
        <div className="hidden text-right text-xs sm:block">
          <p className="font-medium text-slate-200">{user?.display_name}</p>
          <p className="text-slate-500">{user && t(`role.${user.role}`)}</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void logout()}>
          {t("topbar.logout")}
        </button>
      </div>
    </header>
  );
}
