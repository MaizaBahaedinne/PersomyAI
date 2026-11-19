"""Catalogues de l'orchestrateur : statuts des missions et des tâches, priorités."""

MISSION_STATUSES: tuple[str, ...] = ("OPEN", "DONE", "CANCELLED")

TASK_STATUSES: tuple[str, ...] = (
    "OPEN",
    "AWAITING_APPROVAL",
    "APPROVED",
    "RUNNING",
    "DONE",
    "FAILED",
    "REJECTED",
    "CANCELLED",
)

RUN_STATUSES: tuple[str, ...] = ("RUNNING", "SUCCESS", "FAILED")

PRIORITIES: tuple[str, ...] = ("LOW", "NORMAL", "HIGH")

# Statuts depuis lesquels une tâche peut être lancée.
RUNNABLE_STATUSES: frozenset[str] = frozenset({"OPEN", "APPROVED"})

# Statuts où le contenu d'une tâche ne peut plus être modifié.
LOCKED_STATUSES: frozenset[str] = frozenset({"RUNNING", "DONE", "CANCELLED"})

CANCELLABLE_STATUSES: frozenset[str] = frozenset({"OPEN", "AWAITING_APPROVAL", "APPROVED", "FAILED", "REJECTED"})

REOPENABLE_STATUSES: frozenset[str] = frozenset({"FAILED", "REJECTED"})

# Une exécution « RUNNING » plus ancienne est considérée interrompue et peut être rouverte.
STALE_RUNNING_SECONDS = 15 * 60

MAX_OUTPUT_CHARS = 20_000
