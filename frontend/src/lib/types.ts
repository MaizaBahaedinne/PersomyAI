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
  tasks: TaskCounts;
  missions: MissionCounts;
  emergency_stop: boolean;
}

export type TaskStatus =
  | "OPEN"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "RUNNING"
  | "DONE"
  | "FAILED"
  | "REJECTED"
  | "CANCELLED";
export type MissionStatus = "OPEN" | "DONE" | "CANCELLED";
export type Priority = "LOW" | "NORMAL" | "HIGH";

export interface TaskCounts {
  open: number;
  awaiting_approval: number;
  approved: number;
  running: number;
  done: number;
  failed: number;
  rejected: number;
  cancelled: number;
  total: number;
}

export interface MissionCounts {
  open: number;
  done: number;
  cancelled: number;
  total: number;
}

export interface Mission {
  id: string;
  title: string;
  description: string;
  status: MissionStatus;
  created_at: string;
  updated_at: string;
  task_counts: Partial<TaskCounts>;
}

export interface TaskSummary {
  id: string;
  title: string;
  priority: Priority;
  status: TaskStatus;
  mission_id: string | null;
  mission_title: string | null;
  agent_id: string | null;
  agent_name: string | null;
  required_scope: string | null;
  requires_approval: boolean | null;
  created_at: string;
  updated_at: string;
}

export interface Task extends TaskSummary {
  description: string;
  approval_requested_at: string | null;
  decided_by_label: string | null;
  decided_at: string | null;
  decision_reason: string | null;
}

export interface TaskRun {
  id: string;
  status: "RUNNING" | "SUCCESS" | "FAILED";
  provider: string;
  output: string;
  error_code: string | null;
  cost_cents: number;
  tokens_in: number;
  tokens_out: number;
  started_at: string;
  finished_at: string | null;
}

export interface ProviderInfo {
  name: string;
  configured: boolean;
  paid: boolean;
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

export type AutomationStatus = "DRAFT" | "ACTIVE" | "PAUSED";
export type AutomationTriggerType = "TASK_STATUS_CHANGED" | "SCHEDULE";

export interface Automation {
  id: string;
  name: string;
  description: string;
  status: AutomationStatus;
  trigger_type: AutomationTriggerType;
  trigger_config: Record<string, unknown>;
  conditions: Record<string, unknown>[];
  actions: Record<string, unknown>[];
  anti_loop_key: string | null;
  cooldown_seconds: number;
  last_triggered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DepartmentSummary {
  code: string;
  agents_total: number;
  agents_active: number;
  agents_paused: number;
}
