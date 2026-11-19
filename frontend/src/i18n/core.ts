import { en } from "./en";
import { fr, type MessageKey } from "./fr";

export type Locale = "fr" | "en";
export const LOCALES: Locale[] = ["fr", "en"];
export const LOCALE_COOKIE = "persomy_lang";
export const DEFAULT_LOCALE: Locale = "fr";

const dictionaries: Record<Locale, Record<MessageKey, string>> = { fr, en };

export function isLocale(value: unknown): value is Locale {
  return value === "fr" || value === "en";
}

export function isMessageKey(key: string): key is MessageKey {
  return key in fr;
}

export function translate(locale: Locale, key: MessageKey, params?: Record<string, string | number>): string {
  let text: string = dictionaries[locale][key] ?? dictionaries.fr[key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}
