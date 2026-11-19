export type Role = "SUPER_ADMIN" | "ADMIN" | "OPERATOR" | "VIEWER";
export type Language = "fr" | "en";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  preferred_language: Language;
  two_factor_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Me {
  user: User;
  permissions: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditEvent {
  id: string;
  created_at: string;
  actor_label: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  status: "success" | "failure";
  ip_address: string | null;
  details: Record<string, unknown> | null;
}

export interface SessionInfo {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
}

export interface ServiceStatus {
  name: string;
  status: "ok" | "down";
  latency_ms: number | null;
}

export interface DashboardSummary {
  company: { name: string };
  generated_at: string;
  users: { total: number; active: number; disabled: number; super_admins: number };
  sessions: { active: number };
  security: {
    logins_success_24h: number;
    logins_failed_24h: number;
    logins_throttled_24h: number;
    recent_failures: { id: string; created_at: string; action: string; actor_label: string | null; status: string }[];
  };
  recent_activity: { id: string; created_at: string; action: string; actor_label: string | null; status: string }[];
  alerts: { code: string; severity: "info" | "warning"; count: number }[];
  services: ServiceStatus[];
  pending_modules: string[];
  agents: AgentCounts;
  emergency_stop: boolean;
}

export type AgentStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "ERROR" | "DISABLED";

export interface AgentCounts {
  draft: number;
  active: number;
  paused: number;
  error: number;
  disabled: number;
  total: number;
}

export interface AgentSummary {
  id: string;
  identity_key: string;
  name: string;
  department: string;
  role: string;
  skills: string[];
  status: AgentStatus;
  autonomy_level: number;
  updated_at: string;
}

export interface Agent extends AgentSummary {
  description: string;
  mission: string;
  config: Record<string, unknown>;
  max_actions_per_day: number;
  monthly_budget_cents: number;
  access_revoked_at: string | null;
  created_at: string;
  permissions: string[];
  tools: string[];
}

export interface AgentCatalog {
  departments: string[];
  statuses: AgentStatus[];
  settable_statuses: AgentStatus[];
  scopes: { code: string; critical: boolean }[];
  tools: string[];
  autonomy_levels: number[];
}

export interface EmergencyState {
  active: boolean;
  at: string | null;
  by: string | null;
  paused_agents: number;
}

export interface AppSettings {
  company_name: string;
  default_language: Language;
}
