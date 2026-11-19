"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/i18n";
import { ErrorBanner } from "@/components/ui";

export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth();
  const { t } = useI18n();
  if (!can(permission)) return <ErrorBanner message={t("error.permission_denied")} />;
  return <>{children}</>;
}
