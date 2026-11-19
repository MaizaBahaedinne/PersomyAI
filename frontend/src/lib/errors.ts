import { ApiError } from "@/lib/api";
import { isMessageKey } from "@/i18n/core";
import type { MessageKey } from "@/i18n/fr";

export function errorKey(error: unknown): MessageKey {
  if (error instanceof ApiError) {
    const key = `error.${error.code}`;
    if (isMessageKey(key)) return key;
  }
  return "error.unknown";
}

export function formatDateTime(iso: string | null | undefined, locale: string): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}

export function formatTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { timeStyle: "short" }).format(new Date(iso));
}
