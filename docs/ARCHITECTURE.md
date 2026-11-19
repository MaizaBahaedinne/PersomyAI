# Architecture

## Vue d'ensemble

```
Navigateur ──HTTPS──> Caddy ──> frontend (Next.js :3000) ──/api/* (proxy interne)──> backend (FastAPI :8000) ──> PostgreSQL 17
                          └──> backend (api.persomy.com, intégrations externes)
```

- Le navigateur ne parle qu'à `app.persomy.com`. Next.js réécrit `/api/*` vers le backend (variable `BACKEND_INTERNAL_URL`). Les cookies de session sont donc propres à l'hôte de l'application et il n'y a pas de CORS.
- `api.persomy.com` expose la même API pour de futures intégrations (les requêtes modifiantes exigent toujours session + jeton CSRF + origine de confiance si l'en-tête `Origin` est présent).
- PostgreSQL n'est publié sur aucun port.

## Backend (`backend/app`)

Organisation par domaines : `modules/<domaine>/{models,schemas,service,router}.py`.

| Domaine | Contenu |
| --- | --- |
| `authentication` | login/logout, sessions (`auth_sessions`), tentatives (`login_attempts`), CSRF, dépendances FastAPI |
| `users` | comptes, rôles, règles de gestion (dernier SUPER_ADMIN, comptes privilégiés) |
| `permissions` | politique rôle → permissions (`policy.py`) |
| `audit` | `audit_events` en ajout seul, consultation filtrée |
| `settings` | `system_settings` (clé/valeur, liste blanche) |
| `dashboard` | agrégats réels pour le centre de contrôle (dont compteurs d'agents et état de l'arrêt d'urgence) |
| `agents` | agents (identités techniques), cycle de vie, permissions et outils, arrêt d'urgence ; `catalog.py` = statuts, transitions, permissions d'agent, outils |
| `departments` | catalogue en code des départements (pas de table tant qu'ils ne portent pas de données) |
| `core` | configuration, base de données, sécurité (Argon2id, jetons), erreurs, logs JSON |

Domaines prévus non créés : `tasks`, `orchestration`, `automations`, `crm`, `finance`, `analytics`. Les tables ne sont créées que lorsque le besoin fonctionnel existe (migrations Alembic versionnées).

Règles transverses : routes minces, logique dans les services, erreurs centralisées au format `{"error": {"code", "message"}}`, logs JSON sur la sortie standard.

## Base de données

Migration `0001` : `users`, `auth_sessions`, `login_attempts`, `audit_events`, `system_settings`. Migration `0002` : `agents`, `agent_permissions` (clé composite agent/permission), `agent_tools`. Clés étrangères (`ON DELETE CASCADE` pour les sessions, `SET NULL` pour l'audit), index sur les colonnes filtrées, contraintes `CHECK` sur rôles et langues, horodatages UTC.

Les migrations sont appliquées au démarrage du conteneur backend (`alembic upgrade head`). Elles sont additives ; toujours sauvegarder avant déploiement.

## Frontend (`frontend/src`)

- `app/` : routes (App Router). `(app)/` regroupe les pages privées ; `login/` est publique.
- `middleware.ts` : redirige vers `/login` sans cookie de session (filtre de confort ; la vérification réelle est faite par l'API).
- `lib/api.ts` : client HTTP (cookies same-origin, en-tête `X-CSRF-Token`).
- `lib/auth.tsx` : état d'authentification (aucun jeton en `localStorage`).
- `i18n/` : dictionnaires `fr`/`en` typés ; un test garantit la parité des clés.
- Navigation filtrée par permissions ; les modules non développés pointent vers une page « en préparation ».

## Couche IA (prévue)

Interface `Provider` commune (génération, délai d'expiration, comptage de coût, journalisation), implémentations par fournisseur, clés stockées côté serveur uniquement et jamais renvoyées intégralement au frontend. Aucun appel IA n'est effectué aujourd'hui.

## Décisions techniques

- Cookies de session opaques + empreinte SHA-256 en base (plutôt que JWT) : révocation immédiate.
- Proxy Next.js plutôt que CORS : surface d'attaque réduite.
- SQLAlchemy 2 + Alembic : standard FastAPI, migrations versionnées.
- SQLite en mémoire pour les tests rapides ; PostgreSQL pour la production (voir risques dans SECURITY/ROADMAP : migrations non rejouées sur PostgreSQL en local).
