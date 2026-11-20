#!/usr/bin/env bash
# Crée/mettre à jour 10 agents business (5 tunisiens + 5 français) dans Persomy AI.
# Idempotent: rejouable sans dupliquer.
# Usage:
#   DOCKER="sudo docker" ./scripts/seed-business-agents.sh
set -euo pipefail

cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }

DOCKER_CMD="${DOCKER:-docker}"

echo "== Validation docker compose =="
${DOCKER_CMD} compose config -q

echo "== Démarrage backend + db =="
${DOCKER_CMD} compose up -d db backend

echo "== Injection des agents business =="
${DOCKER_CMD} compose exec -T backend python - <<'PY'
import secrets
from sqlalchemy import delete, func, select

from app.core.db import new_session
from app.modules.agents.models import Agent, AgentPermission, AgentTool
from app.modules.users.models import User

AGENTS = [
    {
        "name": "Amina Harbaoui",
        "department": "sales",
        "role": "Directrice commerciale IA",
        "description": "Pilote la croissance commerciale B2B et l'outillage des équipes vente.",
        "mission": "Generer et qualifier des leads B2B, preparer des propositions commerciales et planifier les relances jusqu'au rendez-vous.",
        "skills": ["sales_ops", "lead_scoring", "proposal_writing"],
        "autonomy_level": 2,
        "max_actions_per_day": 35,
        "monthly_budget_cents": 6000,
        "permissions": ["crm:read", "crm:write", "reports:read", "tasks:propose", "email:draft"],
        "tools": ["crm", "documents", "email", "spreadsheet"],
    },
    {
        "name": "Youssef Ben Salem",
        "department": "marketing",
        "role": "Responsable acquisition",
        "description": "Optimise l'acquisition multi-canal et le cout par lead.",
        "mission": "Planifier les campagnes, analyser les performances et proposer des optimisations hebdomadaires sur les canaux d'acquisition.",
        "skills": ["performance_marketing", "ab_testing", "funnel_analysis"],
        "autonomy_level": 2,
        "max_actions_per_day": 30,
        "monthly_budget_cents": 5500,
        "permissions": ["reports:read", "reports:write", "tasks:propose", "documents:write"],
        "tools": ["web_search", "spreadsheet", "documents"],
    },
    {
        "name": "Mariem Trabelsi",
        "department": "customer_service",
        "role": "Responsable relation client",
        "description": "Ameliore la retention client et la qualite des interactions.",
        "mission": "Detecter les risques de churn, produire des plans de retention et structurer les relances clients prioritaires.",
        "skills": ["customer_success", "retention", "nps_improvement"],
        "autonomy_level": 2,
        "max_actions_per_day": 28,
        "monthly_budget_cents": 4500,
        "permissions": ["crm:read", "crm:write", "email:draft", "reports:read", "tasks:propose"],
        "tools": ["crm", "email", "documents"],
    },
    {
        "name": "Mehdi Chahed",
        "department": "finance",
        "role": "Analyste finance operationnelle",
        "description": "Surveille la rentabilite et les derive de couts.",
        "mission": "Suivre la marge et les couts IA, emettre des alertes budgetaires et proposer des simulations de scenario.",
        "skills": ["finance_ops", "cost_control", "scenario_modeling"],
        "autonomy_level": 1,
        "max_actions_per_day": 20,
        "monthly_budget_cents": 3000,
        "permissions": ["finance:read", "finance:simulate", "reports:read", "tasks:propose"],
        "tools": ["spreadsheet", "documents"],
    },
    {
        "name": "Ons Gharbi",
        "department": "hr",
        "role": "Responsable RH operations",
        "description": "Structure les operations RH et le recrutement.",
        "mission": "Prequalifier les candidatures, assister la planification des entretiens et suivre l'onboarding des nouveaux profils.",
        "skills": ["recruitment", "onboarding", "hr_ops"],
        "autonomy_level": 1,
        "max_actions_per_day": 22,
        "monthly_budget_cents": 3500,
        "permissions": ["hr:read", "documents:read", "documents:write", "tasks:propose"],
        "tools": ["documents", "calendar", "email"],
    },
    {
        "name": "Claire Dubois",
        "department": "operations",
        "role": "Directrice operations IA",
        "description": "Coordonne les priorites inter-equipes et l'execution.",
        "mission": "Orchestrer les priorites hebdomadaires, arbitrer les urgences et garantir l'avancement des livrables critiques.",
        "skills": ["ops_management", "prioritization", "delivery_tracking"],
        "autonomy_level": 2,
        "max_actions_per_day": 25,
        "monthly_budget_cents": 7000,
        "permissions": ["reports:read", "reports:write", "tasks:propose", "documents:write"],
        "tools": ["documents", "calendar", "spreadsheet"],
    },
    {
        "name": "Lucas Moreau",
        "department": "marketing",
        "role": "Responsable croissance",
        "description": "Optimise le funnel et le positionnement des offres.",
        "mission": "Analyser la conversion des offres, proposer des ajustements de pricing et prioriser les experimentations de croissance.",
        "skills": ["growth", "pricing", "conversion_optimization"],
        "autonomy_level": 2,
        "max_actions_per_day": 26,
        "monthly_budget_cents": 5000,
        "permissions": ["reports:read", "finance:read", "finance:simulate", "tasks:propose"],
        "tools": ["spreadsheet", "documents", "web_search"],
    },
    {
        "name": "Sophie Lambert",
        "department": "communication",
        "role": "Responsable contenu",
        "description": "Pilote la production de contenu marketing et editorial.",
        "mission": "Produire des plans editoriaux SEO, sequences email et contenus reseaux sociaux alignes sur les objectifs business.",
        "skills": ["content_strategy", "seo", "copywriting"],
        "autonomy_level": 2,
        "max_actions_per_day": 32,
        "monthly_budget_cents": 4000,
        "permissions": ["documents:read", "documents:write", "email:draft", "tasks:propose"],
        "tools": ["documents", "web_search", "email"],
    },
    {
        "name": "Thomas Bernard",
        "department": "sales",
        "role": "Ingenieur avant-vente",
        "description": "Appuie les reponses commerciales techniques.",
        "mission": "Structurer les reponses aux appels d'offres, preparer les demonstrations et formaliser les propositions techniques.",
        "skills": ["pre_sales", "rfp", "solution_design"],
        "autonomy_level": 2,
        "max_actions_per_day": 24,
        "monthly_budget_cents": 5500,
        "permissions": ["crm:read", "crm:write", "documents:write", "reports:read", "tasks:propose"],
        "tools": ["crm", "documents", "email"],
    },
    {
        "name": "Camille Renaud",
        "department": "customer_service",
        "role": "Customer Success Manager",
        "description": "Renforce l'adoption et la valeur client dans la duree.",
        "mission": "Suivre la sante des comptes, proposer des plans d'adoption et identifier les opportunites d'upsell.",
        "skills": ["account_health", "upsell", "customer_success"],
        "autonomy_level": 2,
        "max_actions_per_day": 27,
        "monthly_budget_cents": 4500,
        "permissions": ["crm:read", "crm:write", "reports:read", "email:draft", "tasks:propose"],
        "tools": ["crm", "email", "documents", "spreadsheet"],
    },
]

with new_session() as db:
    actor_id = db.scalar(select(User.id).where(User.role == "SUPER_ADMIN", User.is_active.is_(True)).limit(1))
    if actor_id is None:
        actor_id = db.scalar(select(User.id).where(User.role == "ADMIN", User.is_active.is_(True)).limit(1))

    created = 0
    updated = 0

    for spec in AGENTS:
        agent = db.scalar(select(Agent).where(Agent.name == spec["name"]))
        is_new = agent is None

        if is_new:
            agent = Agent(
                identity_key=f"agt_{secrets.token_hex(8)}",
                name=spec["name"],
                status="ACTIVE",
                created_by=actor_id,
            )
            db.add(agent)
            db.flush()
            created += 1
        else:
            updated += 1

        agent.description = spec["description"]
        agent.department = spec["department"]
        agent.role = spec["role"]
        agent.mission = spec["mission"]
        agent.skills = spec["skills"]
        agent.autonomy_level = int(spec["autonomy_level"])
        agent.config = {"profile": "business", "owner": "persomy"}
        agent.max_actions_per_day = int(spec["max_actions_per_day"])
        agent.monthly_budget_cents = int(spec["monthly_budget_cents"])
        agent.access_revoked_at = None

        current_permissions = set(db.scalars(select(AgentPermission.permission).where(AgentPermission.agent_id == agent.id)).all())
        wanted_permissions = set(spec["permissions"])

        if current_permissions - wanted_permissions:
            db.execute(
                delete(AgentPermission).where(
                    AgentPermission.agent_id == agent.id,
                    AgentPermission.permission.in_(current_permissions - wanted_permissions),
                )
            )
        for permission in sorted(wanted_permissions - current_permissions):
            db.add(AgentPermission(agent_id=agent.id, permission=permission, granted_by=actor_id))

        current_tools = set(db.scalars(select(AgentTool.tool).where(AgentTool.agent_id == agent.id)).all())
        wanted_tools = set(spec["tools"])

        if current_tools - wanted_tools:
            db.execute(
                delete(AgentTool).where(
                    AgentTool.agent_id == agent.id,
                    AgentTool.tool.in_(current_tools - wanted_tools),
                )
            )
        for tool in sorted(wanted_tools - current_tools):
            db.add(AgentTool(agent_id=agent.id, tool=tool, granted_by=actor_id))

    db.commit()

    total = db.scalar(select(func.count()).select_from(Agent)) or 0
    print(f"OK created={created} updated={updated} total={total}")
PY

echo "== Terminé =="
echo "Ouvre la page Agents dans Persomy AI pour voir les 10 profils et leurs missions."
