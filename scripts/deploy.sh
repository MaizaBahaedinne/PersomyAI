#!/usr/bin/env bash
# Déploiement sur le VPS : à lancer MANUELLEMENT après validation (voir docs/DEPLOYMENT.md).
# Étapes : vérifications -> sauvegarde -> build -> démarrage -> contrôle de santé.
# N'utilise jamais "down -v" : les volumes ne sont jamais supprimés.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }
set -a; . ./.env; set +a
# "sudo docker" sur le VPS : DOCKER="sudo docker" ./scripts/deploy.sh
export DOCKER="${DOCKER:-docker}"
[ -n "${POSTGRES_PASSWORD:-}" ] || { echo "POSTGRES_PASSWORD vide" >&2; exit 1; }

echo "== Validation de la configuration Compose =="
${DOCKER} compose config -q

if ${DOCKER} compose ps --status running db 2>/dev/null | grep -q db; then
  echo "== Sauvegarde avant déploiement =="
  ./scripts/backup.sh
else
  echo "Base non démarrée : première installation, pas de sauvegarde."
fi

echo "== Construction des images =="
${DOCKER} compose build

echo "== Démarrage =="
${DOCKER} compose up -d

echo "== Attente de la santé des services =="
for i in $(seq 1 30); do
  unhealthy="$(${DOCKER} compose ps --format '{{.Service}} {{.Health}}' | grep -E 'unhealthy|starting' || true)"
  [ -z "${unhealthy}" ] && break
  sleep 5
done
${DOCKER} compose ps
${DOCKER} compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"
echo "Déploiement terminé. Créez les administrateurs si nécessaire : docs/OPERATIONS.md"
