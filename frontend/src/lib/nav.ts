import type { MessageKey } from "@/i18n/fr";

export interface NavItem {
  href: string;
  label: MessageKey;
  permission?: string;
  soon?: boolean;
}

export const MAIN_NAV: NavItem[] = [{ href: "/dashboard", label: "nav.dashboard", permission: "dashboard:read" }];

/** Modules non développés : liés à une page « en préparation », jamais à de fausses données. */
export const MODULE_NAV: NavItem[] = [
  { href: "/agents", label: "nav.agents", permission: "agents:read" },
  { href: "/missions", label: "nav.missions", permission: "orchestration:read" },
  { href: "/tasks", label: "nav.tasks", permission: "orchestration:read" },
  { href: "/automations", label: "nav.automations", soon: true },
  { href: "/departments", label: "nav.departments", soon: true },
  { href: "/crm", label: "nav.crm", soon: true },
  { href: "/finance", label: "nav.finance", soon: true },
  { href: "/team", label: "nav.team", soon: true },
  { href: "/analytics", label: "nav.analytics", soon: true },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/users", label: "nav.users", permission: "users:read" },
  { href: "/audit", label: "nav.audit", permission: "audit:read" },
  { href: "/settings", label: "nav.settings", permission: "settings:read" },
];

export const SOON_MODULES = MODULE_NAV.filter((m) => m.soon).map((m) => m.href.slice(1));
