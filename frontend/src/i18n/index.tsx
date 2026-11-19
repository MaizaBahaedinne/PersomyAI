"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { LOCALES, LOCALE_COOKIE, isLocale, isMessageKey, translate, type Locale } from "./core";
import type { MessageKey } from "./fr";

export { LOCALES, isLocale };
export type { Locale };

type I18nValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, params?: Record<string, string | number>) => string;
  has: (key: string) => key is MessageKey;
  /** Traduit `prefix.code` si la clé existe, sinon renvoie le code brut. */
  label: (prefix: string, code: string) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ initialLocale, children }: { initialLocale: Locale; children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = next;
  }, []);

  const value = useMemo<I18nValue>(
    () => ({
      locale,
      setLocale,
      t: (key, params) => translate(locale, key, params),
      has: isMessageKey,
      label: (prefix, code) => {
        const key = `${prefix}.${code}`;
        return isMessageKey(key) ? translate(locale, key) : code;
      },
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
