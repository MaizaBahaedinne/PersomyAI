"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/i18n";
import { ADMIN_NAV, MAIN_NAV, MODULE_NAV, type NavItem } from "@/lib/nav";

function Section({ title, items, onNavigate }: { title: string; items: NavItem[]; onNavigate?: () => void }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const pathname = usePathname();
  const visible = items.filter((i) => !i.permission || can(i.permission));
  if (visible.length === 0) return null;
  return (
    <div className="mb-5">
      <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <ul className="space-y-0.5">
        {visible.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
                  active ? "bg-accent-soft/60 text-accent" : "text-slate-300 hover:bg-ink-700/60 hover:text-white"
                }`}
              >
                <span>{t(item.label)}</span>
                {item.soon && (
                  <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-400">
                    {t("nav.soon")}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useI18n();
  return (
    <nav aria-label="Main" className="flex h-full flex-col px-3 py-5">
      <div className="mb-8 flex items-center gap-2 px-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-bold text-ink-950">P</span>
        <span className="text-base font-semibold tracking-tight text-white">{t("app.name")}</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <Section title={t("nav.section.main")} items={MAIN_NAV} onNavigate={onNavigate} />
        <Section title={t("nav.section.modules")} items={MODULE_NAV} onNavigate={onNavigate} />
        <Section title={t("nav.section.admin")} items={ADMIN_NAV} onNavigate={onNavigate} />
      </div>
    </nav>
  );
}
