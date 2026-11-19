"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, api, setUnauthorizedHandler } from "@/lib/api";
import type { Me, User } from "@/lib/types";
import { isLocale, useI18n } from "@/i18n";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthValue {
  status: Status;
  user: User | null;
  permissions: string[];
  can: (permission: string) => boolean;
  login: (email: string, password: string, otp?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setLocale } = useI18n();
  const [status, setStatus] = useState<Status>("loading");
  const [me, setMe] = useState<Me | null>(null);

  const apply = useCallback(
    (value: Me) => {
      setMe(value);
      setStatus("authenticated");
      if (isLocale(value.user.preferred_language)) setLocale(value.user.preferred_language);
    },
    [setLocale],
  );

  const refresh = useCallback(async () => {
    try {
      apply(await api<Me>("/auth/me"));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setMe(null);
        setStatus("anonymous");
      } else {
        throw error;
      }
    }
  }, [apply]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setMe(null);
      setStatus("anonymous");
    });
    refresh().catch(() => setStatus("anonymous"));
    return () => setUnauthorizedHandler(null);
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string, otp?: string) => {
      apply(await api<Me>("/auth/login", { method: "POST", body: otp ? { email, password, otp } : { email, password } }));
    },
    [apply],
  );

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      setMe(null);
      setStatus("anonymous");
    }
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      user: me?.user ?? null,
      permissions: me?.permissions ?? [],
      can: (permission) => !!me?.permissions.includes(permission),
      login,
      logout,
      refresh,
    }),
    [status, me, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
