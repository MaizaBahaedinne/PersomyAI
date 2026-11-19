"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { use } from "react";
import { useI18n } from "@/i18n";
import { SOON_MODULES } from "@/lib/nav";
import { Badge, PageHeader } from "@/components/ui";

export default function ComingSoonPage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = use(params);
  const { t } = useI18n();
  if (!SOON_MODULES.includes(module)) notFound();
  const name = t(`nav.${module}` as never);
  return (
    <div>
      <PageHeader title={name} actions={<Badge tone="info">{t("dashboard.module_pending")}</Badge>} />
      <div className="card max-w-xl space-y-4">
        <h2 className="text-lg font-semibold text-white">{t("coming.title")}</h2>
        <p className="text-sm text-slate-300">{t("coming.description", { name })}</p>
        <Link href="/dashboard" className="btn-secondary">
          {t("coming.back")}
        </Link>
      </div>
    </div>
  );
}
