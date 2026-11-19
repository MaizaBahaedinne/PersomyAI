import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { I18nProvider, type Locale } from "@/i18n";

export function renderWithI18n(ui: ReactElement, locale: Locale = "fr") {
  return render(<I18nProvider initialLocale={locale}>{ui}</I18nProvider>);
}

export function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

export const adminUser = {
  id: "u1",
  email: "admin@example.com",
  display_name: "Admin",
  role: "SUPER_ADMIN" as const,
  is_active: true,
  preferred_language: "fr" as const,
  two_factor_enabled: false,
  last_login_at: null,
  created_at: "2026-01-01T00:00:00Z",
};
