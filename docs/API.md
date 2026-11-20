# API

Base : `/api/v1` (UI : `https://app.persomy.com/api/v1`, intégrations : `https://api.persomy.com/api/v1`). Santé : `GET /health`, `GET /health/ready`.

Authentification : cookie de session `persomy_session` (HttpOnly). Les requêtes modifiantes exigent l'en-tête `X-CSRF-Token` (valeur du cookie `persomy_csrf`). Documentation interactive : `/api/docs` hors production uniquement.

Erreurs : `{"error": {"code": "...", "message": "...", "details": [...]}}`.

## Authentification

| Méthode | Route | Permission | Description |
| --- | --- | --- | --- |
| POST | `/auth/login` | publique | `{email, password, otp?}` → utilisateur + permissions, pose les cookies. 401 générique, 429 si bloqué. Si la 2FA est active : sans `otp` → 401 `two_factor_required` (aucune session, aucun échec compté) ; `otp` faux → 401 `invalid_otp` (compté par l'anti force brute) |
| GET | `/auth/2fa` | session | `{enabled, available, recovery_codes_left}` (`available` = `TWO_FACTOR_KEY` valide) |
| POST | `/auth/2fa/setup` | session | `{password}` → `{secret, otpauth_uri}` (affichés une seule fois). 409 `two_factor_already_enabled`, 409 `two_factor_unavailable` |
| POST | `/auth/2fa/enable` | session | `{code}` → `{recovery_codes}` (10 codes, affichés une seule fois) ; révoque les autres sessions. 409 `two_factor_not_started`, 401 `invalid_otp` |
| POST | `/auth/2fa/disable` | session | `{password, code}` → 204. 409 `two_factor_not_enabled`, 401 `invalid_credentials` / `invalid_otp` |
| POST | `/auth/2fa/recovery-codes` | session | `{password, code}` → nouveaux `{recovery_codes}` (les anciens sont invalidés) |
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

Codes d'erreur spécifiques : `agent_not_found` (404), `status_unchanged`, `agent_name_taken`, `invalid_transition`, `agent_incomplete`, `access_revoked`, `emergency_stop_active`, `agent_not_deletable` (409), `super_admin_required` (403).

## Automatisations

Préfixe `/api/v1/automations`.

| Méthode | Route | Permission | Description |
| --- | --- | --- | --- |
| GET | `/automations?search&status&trigger_type&limit&offset` | `automations:read` | Liste filtrable (`DRAFT`/`ACTIVE`/`PAUSED`, `TASK_STATUS_CHANGED`/`SCHEDULE`) |
| POST | `/automations` | `automations:write` | Crée une automatisation en `DRAFT` |
| GET | `/automations/{id}` | `automations:read` | Détail |
| PATCH | `/automations/{id}` | `automations:write` | Modifie nom, déclencheur, conditions, actions, garde-fou |
| POST | `/automations/{id}/status` | `automations:write` | Change le statut (`DRAFT`/`ACTIVE`/`PAUSED`) |
| POST | `/automations/{id}/simulate-trigger` | `automations:write` | Simule un événement (`event_key`) et applique la protection anti-boucle (`anti_loop_key`, `cooldown_seconds`) |

Codes d'erreur principaux : `automation_not_found`, `automation_action_required`, `automation_loop_risk`, `automation_name_taken`, `automation_status_unchanged`, `automation_not_active`, `automation_loop_blocked`.

## Missions et tâches (orchestrateur)

Préfixes `/api/v1/missions` et `/api/v1/tasks`. Les routes statiques (`/tasks/provider`) sont déclarées avant `/{id}`.

| Méthode | Route | Permission |
| --- | --- | --- |
| GET | `/missions?search&status&limit&offset` | `orchestration:read` (chaque mission porte `task_counts`) |
| POST | `/missions` | `orchestration:write` |
| GET / PATCH | `/missions/{id}` | `orchestration:read` / `orchestration:write` (statuts OPEN, DONE, CANCELLED) |
| GET | `/tasks/provider` | `orchestration:read` (`{name, configured, paid}`) |
| GET | `/tasks?search&status&agent_id&mission_id&limit&offset` | `orchestration:read` |
| POST | `/tasks` | `orchestration:write` (mission ouverte, agent non désactivé) |
| GET / PATCH | `/tasks/{id}` | `orchestration:read` / `orchestration:write` (`agent_id` ou `required_scope` à `null` les retirent ; modifier le contenu d'une tâche en attente ou approuvée réinitialise la validation) |
| POST | `/tasks/{id}/request-approval` | `orchestration:write` |
| POST | `/tasks/{id}/approve` | `orchestration:approve` (corps facultatif `{comment}`) |
| POST | `/tasks/{id}/reject` | `orchestration:approve` (corps `{reason}` obligatoire) |
| POST | `/tasks/{id}/cancel` | `orchestration:write` (depuis OPEN, AWAITING_APPROVAL, APPROVED, FAILED, REJECTED) |
| POST | `/tasks/{id}/reopen` | `orchestration:write` (FAILED, REJECTED, ou RUNNING bloquée depuis plus de 15 min) |
| POST | `/tasks/{id}/run` | `orchestration:run` (répond `{task, run}`) |
| GET | `/tasks/{id}/runs` | `orchestration:read` |
| GET | `/tasks/{id}/history` | `orchestration:read` (audit de la tâche) |

Statuts de tâche : OPEN, AWAITING_APPROVAL, APPROVED, RUNNING, DONE, FAILED, REJECTED, CANCELLED.

Contrôles de `POST /tasks/{id}/run`, dans cet ordre (chaque refus est audité `task.run_blocked`, sans créer d'exécution) : `mission_not_open`, `agent_required`, `emergency_stop_active`, `agent_not_active` (inclut l'accès révoqué), `scope_not_granted`, `approval_required`, `provider_not_configured`, `daily_quota_exceeded`, `budget_exceeded` (409). Autres codes : `mission_not_found`, `task_not_found` (404), `agent_not_assignable`, `approval_not_required`, `invalid_task_state` (409), `self_approval_forbidden` (403).

## Autres

| Méthode | Route | Permission |
| --- | --- | --- |
| GET | `/dashboard/summary` | `dashboard:read` |
| GET | `/departments/summary` | `dashboard:read` |
| GET | `/audit?action&status&actor&since&limit&offset` | `audit:read` |
| GET / PUT | `/settings` | `settings:read` / `settings:write` |

## Rôles et permissions

| Rôle | Permissions |
| --- | --- |
| SUPER_ADMIN | toutes |
| ADMIN | dashboard, users (lecture/écriture limitée aux rôles non privilégiés), audit, settings (lecture), révocation de sessions, agents (lecture/écriture, arrêt d'urgence), orchestration (lecture, écriture, validation, exécution), automatisations (lecture/écriture) |
| OPERATOR | dashboard, users (lecture), settings (lecture), agents (lecture), orchestration (lecture), automatisations (lecture) |
| VIEWER | dashboard |
