# API

Base : `/api/v1` (UI : `https://app.persomy.com/api/v1`, intégrations : `https://api.persomy.com/api/v1`). Santé : `GET /health`, `GET /health/ready`.

Authentification : cookie de session `persomy_session` (HttpOnly). Les requêtes modifiantes exigent l'en-tête `X-CSRF-Token` (valeur du cookie `persomy_csrf`). Documentation interactive : `/api/docs` hors production uniquement.

Erreurs : `{"error": {"code": "...", "message": "...", "details": [...]}}`.

## Authentification

| Méthode | Route | Permission | Description |
| --- | --- | --- | --- |
| POST | `/auth/login` | publique | `{email, password}` → utilisateur + permissions, pose les cookies. 401 générique, 429 si bloqué |
| POST | `/auth/logout` | session | Révoque la session |
| GET | `/auth/me` | session | Utilisateur et permissions |
| PATCH | `/auth/me` | session | `display_name`, `preferred_language` |
| POST | `/auth/change-password` | session | Révoque les autres sessions |
| GET | `/auth/sessions` | session | Sessions actives du compte |
| DELETE | `/auth/sessions/{id}` | session | Révoque une session du compte |

## Utilisateurs

| Méthode | Route | Permission |
| --- | --- | --- |
| GET | `/users?search&role&active&limit&offset` | `users:read` |
| POST | `/users` | `users:write` (rôles `ADMIN`/`SUPER_ADMIN` : SUPER_ADMIN uniquement) |
| GET | `/users/{id}` | `users:read` |
| PATCH | `/users/{id}` | `users:write` (règles de protection) |
| PUT | `/users/{id}/password` | `users:write` + SUPER_ADMIN |
| DELETE | `/users/{id}/sessions` | `sessions:revoke` |

## Agents IA

Préfixe `/api/v1/agents`. Les routes statiques sont déclarées avant `/{id}`.

| Méthode | Route | Permission |
| --- | --- | --- |
| GET | `/agents/catalog` | `agents:read` (départements, statuts, permissions d'agent, outils, niveaux d'autonomie) |
| GET | `/agents?search&status&department&limit&offset` | `agents:read` |
| POST | `/agents` | `agents:write` (création en DRAFT, sans accès ; budget > 0 : SUPER_ADMIN) |
| GET | `/agents/{id}` | `agents:read` |
| PATCH | `/agents/{id}` | `agents:write` (augmenter l'autonomie ou le budget : `agents:grant`) |
| POST | `/agents/{id}/status` | `agents:write` (transitions contrôlées ; `ERROR` non ciblable) |
| PUT | `/agents/{id}/permissions` | `agents:grant` |
| PUT | `/agents/{id}/tools` | `agents:grant` |
| POST | `/agents/{id}/revoke-access` | `agents:grant` (retire permissions et outils, désactive) |
| DELETE | `/agents/{id}` | `agents:delete` (seulement DRAFT ou DISABLED) |
| GET | `/agents/{id}/history` | `agents:read` (événements d'audit de l'agent) |
| GET | `/agents/emergency-stop` | `agents:read` |
| POST | `/agents/emergency-stop` | `agents:write` (suspend tous les agents actifs, bloque toute activation) |
| DELETE | `/agents/emergency-stop` | `agents:grant` (libère ; les agents restent en pause) |

Codes d'erreur spécifiques : `agent_not_found` (404), `agent_name_taken`, `status_unchanged`, `invalid_transition`, `agent_incomplete`, `access_revoked`, `emergency_stop_active`, `agent_not_deletable` (409), `super_admin_required` (403).

## Autres

| Méthode | Route | Permission |
| --- | --- | --- |
| GET | `/dashboard/summary` | `dashboard:read` |
| GET | `/audit?action&status&actor&since&limit&offset` | `audit:read` |
| GET / PUT | `/settings` | `settings:read` / `settings:write` |

## Rôles et permissions

| Rôle | Permissions |
| --- | --- |
| SUPER_ADMIN | toutes |
| ADMIN | dashboard, users (lecture/écriture limitée aux rôles non privilégiés), audit, settings (lecture), révocation de sessions, agents (lecture/écriture, arrêt d'urgence) |
| OPERATOR | dashboard, users (lecture), settings (lecture), agents (lecture) |
| VIEWER | dashboard |
