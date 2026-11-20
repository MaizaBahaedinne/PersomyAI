"""Rôles et permissions. Les permissions sont vérifiées côté serveur uniquement."""

from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    DASHBOARD_READ = "dashboard:read"
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    AUDIT_READ = "audit:read"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    SESSIONS_REVOKE = "sessions:revoke"
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"  # créer, modifier, changer le statut, arrêt d'urgence
    AGENTS_GRANT = "agents:grant"  # permissions, outils, autonomie, levée d'arrêt d'urgence, révocation
    AGENTS_DELETE = "agents:delete"
    ORCHESTRATION_READ = "orchestration:read"
    ORCHESTRATION_WRITE = "orchestration:write"  # missions et tâches : créer, modifier, affecter, annuler
    ORCHESTRATION_APPROVE = "orchestration:approve"  # valider ou rejeter une tâche sensible
    ORCHESTRATION_RUN = "orchestration:run"  # lancer l'exécution d'une tâche
    AUTOMATIONS_READ = "automations:read"
    AUTOMATIONS_WRITE = "automations:write"
    CRM_READ = "crm:read"
    CRM_WRITE = "crm:write"
    FINANCE_READ = "finance:read"
    FINANCE_SIMULATE = "finance:simulate"
    TEAM_READ = "team:read"


_ALL = set(Permission)

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: _ALL,
    Role.ADMIN: {
        Permission.DASHBOARD_READ,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.AUDIT_READ,
        Permission.SETTINGS_READ,
        Permission.SESSIONS_REVOKE,
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.ORCHESTRATION_READ,
        Permission.ORCHESTRATION_WRITE,
        Permission.ORCHESTRATION_APPROVE,
        Permission.ORCHESTRATION_RUN,
        Permission.AUTOMATIONS_READ,
        Permission.AUTOMATIONS_WRITE,
        Permission.CRM_READ,
        Permission.CRM_WRITE,
        Permission.FINANCE_READ,
        Permission.FINANCE_SIMULATE,
        Permission.TEAM_READ,
    },
    Role.OPERATOR: {
        Permission.DASHBOARD_READ,
        Permission.USERS_READ,
        Permission.SETTINGS_READ,
        Permission.AGENTS_READ,
        Permission.ORCHESTRATION_READ,
        Permission.AUTOMATIONS_READ,
        Permission.CRM_READ,
        Permission.FINANCE_READ,
        Permission.FINANCE_SIMULATE,
        Permission.TEAM_READ,
    },
    Role.VIEWER: {Permission.DASHBOARD_READ},
}


def permissions_for(role: Role | str) -> set[Permission]:
    return ROLE_PERMISSIONS.get(Role(role), set())


def has_permission(role: Role | str, permission: Permission) -> bool:
    return permission in permissions_for(role)
