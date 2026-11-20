#!/usr/bin/env bash
# Crée ou met à jour un agent "General Manager AI Agent" pour le dispatching des tâches
# et la définition des missions dans Persomy AI.
# Usage:
#   DOCKER="sudo docker" ./scripts/set-general-manager-agent.sh
set -euo pipefail

cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }

DOCKER_CMD="${DOCKER:-docker}"

echo "== Validation docker compose =="
${DOCKER_CMD} compose config -q

echo "== Démarrage backend + db =="
${DOCKER_CMD} compose up -d db backend

echo "== Création / mise à jour General Manager AI Agent =="
${DOCKER_CMD} compose exec -T backend python - <<'PY'
import secrets
from sqlalchemy import delete, select

from app.core.db import new_session
from app.modules.agents.models import Agent, AgentPermission, AgentTool
from app.modules.users.models import User

NAME = "General Manager AI Agent"

PERMISSIONS = {
    "tasks:propose",
    "reports:read",
    "reports:write",
    "crm:read",
    "finance:read",
    "hr:read",
    "documents:read",
    "documents:write",
    "email:draft",
}

TOOLS = {
    "documents",
    "crm",
    "spreadsheet",
    "calendar",
    "email",
    "web_search",
}

with new_session() as db:
    actor_id = db.scalar(select(User.id).where(User.role == "SUPER_ADMIN", User.is_active.is_(True)).limit(1))
    if actor_id is None:
        actor_id = db.scalar(select(User.id).where(User.role == "ADMIN", User.is_active.is_(True)).limit(1))

    agent = db.scalar(select(Agent).where(Agent.name == NAME))
    created = False

    if agent is None:
        agent = Agent(
            identity_key=f"agt_{secrets.token_hex(8)}",
            name=NAME,
            description="Agent de pilotage global: transforme les objectifs en missions et distribue les tâches aux bons agents.",
            department="executive",
            role="General Manager IA",
            mission=(
                "Définir les missions opérationnelles à partir des objectifs business, découper en tâches actionnables, "
                "attribuer les tâches aux agents spécialisés et produire un reporting de suivi."
            ),
            skills=["mission_design", "task_dispatching", "ops_prioritization", "kpi_tracking"],
            status="ACTIVE",
            autonomy_level=2,
            config={"profile": "general_manager", "owner": "persomy"},
            max_actions_per_day=40,
            monthly_budget_cents=7000,
            created_by=actor_id,
        )
        db.add(agent)
        db.flush()
        created = True
    else:
        agent.description = "Agent de pilotage global: transforme les objectifs en missions et distribue les tâches aux bons agents."
        agent.department = "executive"
        agent.role = "General Manager IA"
        agent.mission = (
            "Définir les missions opérationnelles à partir des objectifs business, découper en tâches actionnables, "
            "attribuer les tâches aux agents spécialisés et produire un reporting de suivi."
        )
        agent.skills = ["mission_design", "task_dispatching", "ops_prioritization", "kpi_tracking"]
        agent.status = "ACTIVE"
        agent.autonomy_level = 2
        agent.config = {"profile": "general_manager", "owner": "persomy"}
        agent.max_actions_per_day = 40
        agent.monthly_budget_cents = 7000
        agent.access_revoked_at = None

    current_permissions = set(
        db.scalars(select(AgentPermission.permission).where(AgentPermission.agent_id == agent.id)).all()
    )
    if current_permissions - PERMISSIONS:
        db.execute(
            delete(AgentPermission).where(
                AgentPermission.agent_id == agent.id,
                AgentPermission.permission.in_(current_permissions - PERMISSIONS),
            )
        )
    for permission in sorted(PERMISSIONS - current_permissions):
        db.add(AgentPermission(agent_id=agent.id, permission=permission, granted_by=actor_id))

    current_tools = set(db.scalars(select(AgentTool.tool).where(AgentTool.agent_id == agent.id)).all())
    if current_tools - TOOLS:
        db.execute(
            delete(AgentTool).where(
                AgentTool.agent_id == agent.id,
                AgentTool.tool.in_(current_tools - TOOLS),
            )
        )
    for tool in sorted(TOOLS - current_tools):
        db.add(AgentTool(agent_id=agent.id, tool=tool, granted_by=actor_id))

    db.commit()

    print(f"OK name={agent.name} created={created} status={agent.status} autonomy={agent.autonomy_level}")
PY

echo "== Terminé =="
echo "Agent prêt: General Manager AI Agent (visible dans la page Agents)."
