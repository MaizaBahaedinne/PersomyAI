"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/i18n";
import { LanguageSwitch } from "@/components/Topbar";

export function LoginForm() {
  const { t } = useI18n();
  const { login, status } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [needOtp, setNeedOtp] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password, needOtp ? otp.trim() : undefined);
      router.replace("/dashboard");
    } catch (e) {
      if (e instanceof ApiError && e.code === "two_factor_required") {
        setNeedOtp(true);
        setOtp("");
        return;
      }
      if (e instanceof ApiError && e.code === "invalid_otp") {
        setError(t("login.error.invalid_otp"));
        setOtp("");
        return;
      }
      if (e instanceof ApiError && e.code === "login_throttled") {
        setError(t("login.error.throttled", { minutes: Math.max(1, Math.ceil((e.retryAfter ?? 60) / 60)) }));
      } else if (e instanceof ApiError && e.status === 401) {
        setError(t("login.error.invalid_credentials"));
      } else if (e instanceof ApiError) {
        setError(t("common.error"));
      } else {
        setError(t("login.error.network"));
      }
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="absolute right-4 top-4">
        <LanguageSwitch />
      </div>
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-xl font-bold text-ink-950">P</span>
          <h1 className="text-2xl font-semibold tracking-tight text-white">{t("app.name")}</h1>
          <p className="text-sm text-slate-400">{t("login.subtitle")}</p>
        </div>
        <form onSubmit={submit} className="card space-y-4" aria-label={t("login.title")}>
          <div>
            <label htmlFor="email" className="label">
              {t("login.email")}
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="label">
              {t("login.password")}
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {needOtp && (
            <div>
              <label htmlFor="otp" className="label">
                {t("login.otp")}
              </label>
              <input
                id="otp"
                type="text"
                autoComplete="one-time-code"
                autoFocus
                required
                className="input"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
              />
              <p className="mt-1 text-xs text-slate-500">{t("login.otp_hint")}</p>
            </div>
          )}
          {error && (
            <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          )}
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? t("login.submitting") : t("login.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
