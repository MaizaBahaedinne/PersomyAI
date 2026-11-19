#!/usr/bin/env bash
# Déploiement sur le VPS : à lancer MANUELLEMENT après validation (voir docs/DEPLOYMENT.md).
# Étapes : vérifications -> sauvegarde -> build -> démarrage -> contrôle de santé.
# N'utilise jamais "down -v" : les volumes ne sont jamais supprimés.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }
set -a; . ./.env; set +a
[ -n "${POSTGRES_PASSWORD:-}" ] || { echo "POSTGRES_PASSWORD vide" >&2; exit 1; }

echo "== Validation de la configuration Compose =="
docker compose config -q

if docker compose ps --status running db 2>/dev/null | grep -q db; then
  echo "== Sauvegarde avant déploiement =="
  ./scripts/backup.sh
else
  echo "Base non démarrée : première installation, pas de sauvegarde."
fi

echo "== Construction des images =="
docker compose build

echo "== Démarrage =="
docker compose up -d

echo "== Attente de la santé des services =="
for i in $(seq 1 30); do
  unhealthy="$(docker compose ps --format '{{.Service}} {{.Health}}' | grep -E 'unhealthy|starting' || true)"
  [ -z "${unhealthy}" ] && break
  sleep 5
done
docker compose ps
docker compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"
echo "Déploiement terminé. Créez les administrateurs si nécessaire : docs/OPERATIONS.md"
