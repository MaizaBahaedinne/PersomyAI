# Persomy AI

Plateforme de pilotage d'une entreprise gérée par deux administrateurs humains et assistée, progressivement, par des agents IA spécialisés.

- Application : https://app.persomy.com
- API : https://api.persomy.com
- Langues : français et anglais

## État du projet

| Module | État |
| --- | --- |
| Authentification, sessions, CSRF, anti force brute, rôles/permissions, audit | Terminé et testé (tests automatisés) |
| Gestion des utilisateurs, paramètres généraux | Terminé et testé |
| Centre de contrôle (données réelles : utilisateurs, sessions, sécurité, services) | Terminé et testé |
| Agents IA (identités techniques, statuts, permissions, outils, historique, arrêt d'urgence) | Terminé et testé (gestion uniquement : aucun agent n'exécute encore de tâche ni n'appelle de modèle IA) |
| Orchestrateur (missions, tâches, validation humaine, interface fournisseur IA) | Développé et testé (tests automatisés) ; **aucun fournisseur IA réel n'existe** : l'exécution d'une tâche répond `provider_not_configured`, rien n'est simulé |
| Automatisations | Développé et testé (SQLite, tests automatisés) : workflows configurables, déclencheurs `TASK_STATUS_CHANGED` / `SCHEDULE`, garde-fou anti-boucle (clé + cooldown), audit ; exécution métier réelle encore à connecter |
| Départements | Développé et testé (lecture réelle): synthèse des agents par département |
| CRM, finance, RH, analytics | Non implémenté (pages « en préparation », aucune donnée fictive) |
| Authentification à deux facteurs (TOTP + codes de secours) | Développé et testé (SQLite, tests automatisés) ; non vérifié sur PostgreSQL ; facultative (non imposée) ; pas de QR code (saisie manuelle de la clé) ; exige `TWO_FACTOR_KEY` |
| Déploiement VPS | Réalisé manuellement sur un VPS (migrations 0001 à 0003 appliquées) ; les évolutions suivantes (migration 0004, 2FA) sont à déployer avec validation humaine |

Détail dans [docs/ROADMAP.md](docs/ROADMAP.md).

## Pile technique

- Frontend : Next.js 15, React 19, TypeScript, Tailwind CSS 3
- Backend : Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, Argon2id
- Base de données : PostgreSQL 17
- Infrastructure : Docker Compose, Caddy (HTTPS)

## Structure

```
backend/    API FastAPI (app/modules/*, migrations/, tests/)
frontend/   Application Next.js (src/app, src/components, src/i18n)
scripts/    backup.sh, restore.sh, deploy.sh
docs/       documentation
Caddyfile, docker-compose.yml, .env.example
```

## Développement local

Backend (Python 3.12 ou supérieur) :

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest            # tests (SQLite en mémoire)
ruff check .
```

Frontend (Node 22) :

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run build
```

Les tests backend n'utilisent jamais la base de développement ni de production.

## Configuration

Copier `.env.example` vers `.env` et renseigner `POSTGRES_PASSWORD` (`openssl rand -hex 32`). Aucun secret n'est versionné. Variables documentées dans [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Créer les deux administrateurs

Aucun mot de passe par défaut n'existe. Procédure dans [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Documentation

[Vision](docs/VISION.md) · [Architecture](docs/ARCHITECTURE.md) · [Sécurité](docs/SECURITY.md) · [Roadmap](docs/ROADMAP.md) · [Déploiement](docs/DEPLOYMENT.md) · [Exploitation](docs/OPERATIONS.md) · [API](docs/API.md)
