import type { Metadata } from "next";
import { cookies } from "next/headers";
import type { ReactNode } from "react";
import { I18nProvider } from "@/i18n";
import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale } from "@/i18n/core";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Persomy AI",
  description: "Persomy AI - centre de contrôle de l'entreprise assistée par IA",
  robots: { index: false, follow: false },
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const stored = (await cookies()).get(LOCALE_COOKIE)?.value;
  const locale = isLocale(stored) ? stored : DEFAULT_LOCALE;
  return (
    <html lang={locale}>
      <body>
        <I18nProvider initialLocale={locale}>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
