"""Catalogues des agents : statuts, transitions, permissions et outils autorisables.

Les permissions d'agent sont un espace de noms distinct des permissions humaines (`app.modules.permissions`).
Aucune permission d'administration (utilisateurs, paramètres, audit, sessions, agents) n'existe ici : un agent ne
peut donc jamais en recevoir. Aucun paiement ni virement n'est au catalogue.
"""

STATUSES: tuple[str, ...] = ("DRAFT", "ACTIVE", "PAUSED", "ERROR", "DISABLED")

# Statuts ciblables via l'API (ERROR est réservé au système / à l'orchestrateur).
SETTABLE_STATUSES: tuple[str, ...] = ("DRAFT", "ACTIVE", "PAUSED", "DISABLED")

TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("DRAFT", "ACTIVE"),
        ("DRAFT", "DISABLED"),
        ("ACTIVE", "PAUSED"),
        ("ACTIVE", "DISABLED"),
        ("PAUSED", "ACTIVE"),
        ("PAUSED", "DISABLED"),
        ("ERROR", "ACTIVE"),
        ("ERROR", "PAUSED"),
        ("ERROR", "DISABLED"),
        ("DISABLED", "DRAFT"),
    }
)

DELETABLE_STATUSES: frozenset[str] = frozenset({"DRAFT", "DISABLED"})

# code -> critique ? Une permission critique impliquera toujours une validation humaine (orchestrateur, phase 4).
SCOPES: dict[str, bool] = {
    "crm:read": False,
    "crm:write": False,
    "documents:read": False,
    "documents:write": False,
    "reports:read": False,
    "reports:write": False,
    "email:draft": False,
    "email:send": True,
    "social:publish": True,
    "finance:read": False,
    "finance:simulate": False,
    "hr:read": False,
    "tasks:propose": False,
}

TOOLS: tuple[str, ...] = (
    "web_search",
    "email",
    "calendar",
    "documents",
    "crm",
    "spreadsheet",
    "code_sandbox",
)

AUTONOMY_LEVELS: tuple[int, ...] = (1, 2, 3)
