# Déploiement

**Aucun déploiement n'a été exécuté.** Toute opération sur le VPS OVH nécessite une validation humaine explicite. Le VPS historique du site Laravel, le DNS et le pare-feu ne sont pas concernés.

## Prérequis VPS

Ubuntu 24.04, Docker Engine + plugin Compose, ports 80/443 ouverts, DNS `app.persomy.com` et `api.persomy.com` déjà pointés vers le VPS.

## Variables d'environnement (`.env`)

| Variable | Rôle | Exemple / défaut |
| --- | --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | Base PostgreSQL | `persomy` |
| `POSTGRES_PASSWORD` | Mot de passe (obligatoire, secret) | `openssl rand -hex 32` |
| `APP_ENV` | `production` désactive `/api/docs` | `production` |
| `TRUSTED_ORIGINS` | Origines acceptées pour les requêtes modifiantes | `https://app.persomy.com` |
| `COOKIE_SECURE` | Cookies `Secure` | `true` |
| `COOKIE_SAMESITE` | `lax` ou `strict` | `lax` |
| `SESSION_ABSOLUTE_HOURS` / `SESSION_IDLE_MINUTES` | Durées de session | `12` / `120` |
| `LOGIN_MAX_FAILURES_PER_ACCOUNT` / `_PER_IP` / `LOGIN_WINDOW_MINUTES` | Anti force brute | `5` / `20` / `15` |
| `LOG_LEVEL` | Niveau de logs | `INFO` |
| `BACKEND_INTERNAL_URL` | Cible interne du proxy Next.js (fixée au build) | `http://backend:8000` |

`DATABASE_URL` est assemblée par `docker-compose.yml`. Ne jamais committer `.env`.

## Procédure (après validation)

1. Sur le VPS, **inventorier l'existant** sans rien modifier : `docker compose ls`, `docker volume ls`, `docker ps`, contenu du Caddyfile actuel.
2. Aligner `docker-compose.yml` sur l'existant : noms de volumes (`pgdata`, `caddy_data`, `caddy_config`) et réseau. Si une base PostgreSQL existe déjà avec des données, **ne pas la réutiliser sans sauvegarde** et valider la compatibilité du schéma (les tables de Persomy AI sont nouvelles ; la migration `0001` ne supprime rien).
3. Cloner le dépôt, `cp .env.example .env`, renseigner les secrets.
4. `./scripts/backup.sh` si une base existe.
5. `./scripts/deploy.sh` (valide la config, sauvegarde, construit, démarre, contrôle la santé).
6. Créer les deux administrateurs (voir [OPERATIONS.md](OPERATIONS.md)).
7. Vérifier : `https://api.persomy.com/health/ready`, connexion sur `https://app.persomy.com`.

Si le Caddy existant sert déjà d'autres sites, ne pas le remplacer : ajouter uniquement les blocs de `Caddyfile` à la configuration existante.

## Retour arrière

- Application : `git checkout <tag précédent> && ./scripts/deploy.sh`.
- Données : `./scripts/restore.sh backups/<fichier>.dump` (confirmation « RESTAURER » demandée, sauvegarde de sécurité automatique).
- Ne jamais exécuter `docker compose down -v`.

## Healthchecks

`db` : `pg_isready` · `backend` : `GET /health/ready` (vérifie la base) · `frontend` : `GET /login`. L'ordre de démarrage dépend de ces contrôles. **Non vérifiés en conditions réelles** (Docker non disponible en développement).
