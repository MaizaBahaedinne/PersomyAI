# Déploiement

**Un premier déploiement a été réalisé manuellement sur le VPS OVH (pile `persomy`, migrations 0001 à 0003).** Toute nouvelle opération sur le VPS (mise à jour, bascule, nettoyage d'une ancienne pile) nécessite une validation humaine explicite. Le DNS et le pare-feu ne sont pas concernés par ce dépôt.

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
| `TWO_FACTOR_KEY` | Clé Fernet chiffrant les secrets 2FA ; sans elle la 2FA est indisponible. À sauvegarder hors du VPS | voir OPERATIONS.md |
| `AI_PROVIDER` | Fournisseur IA (aucun n'est implémenté : laisser vide) | vide |
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

## Pièges rencontrés lors du premier déploiement

- **`docker-entrypoint.sh: Permission denied`** (backend en boucle de redémarrage) : cause probable, un `umask 077` lors du `git clone` qui retire le bit exécutable ou la lecture. Cloner avec `umask 022`, ou corriger : `chmod +x backend/docker-entrypoint.sh` puis reconstruire l'image.
- **Docker sans `sudo`** : si l'utilisateur n'est pas dans le groupe `docker`, préfixer par `sudo docker …` ou lancer les scripts avec `DOCKER="sudo docker"`.
- **Plusieurs piles Compose sur le même VPS** : le nom de projet Compose (dossier ou `-p`) détermine les noms de conteneurs et de volumes (`<projet>_pgdata`). Ne jamais réutiliser ni supprimer les volumes d'une autre pile sans sauvegarde et accord explicite.
- **Caddy existant sur 80/443** : tant qu'un ancien Caddy détient ces ports, il sert l'ancien site (ex. 404 sur `/login`). Bascule : arrêter l'ancien (`docker stop <ancien-caddy>`, **sans** supprimer ses volumes), puis `docker compose up -d caddy` dans la nouvelle pile. Retour arrière : `docker compose stop caddy` puis `docker start <ancien-caddy>`. Après un redémarrage du VPS, vérifier quel conteneur détient 80/443 (politique `restart` de l'ancien Caddy).
- **CLI** : `docker compose exec backend python -m app.cli …` (sur une seule ligne ; avec `sudo docker` sur le VPS).
- **Mise à jour** : `git pull --ff-only`, puis `docker compose build && docker compose up -d` (reconstruction nécessaire si `requirements.txt` change). Les migrations s'appliquent au démarrage ; vérifier `alembic_version` (0004 attendu après l'ajout de la 2FA).

## Retour arrière

- Application : `git checkout <tag précédent> && ./scripts/deploy.sh`.
- Données : `./scripts/restore.sh backups/<fichier>.dump` (confirmation « RESTAURER » demandée, sauvegarde de sécurité automatique).
- Ne jamais exécuter `docker compose down -v`.

## Healthchecks

`db` : `pg_isready` · `backend` : `GET /health/ready` (vérifie la base) · `frontend` : `GET /login`. L'ordre de démarrage dépend de ces contrôles. **Non vérifiés en conditions réelles** (Docker non disponible en développement).
