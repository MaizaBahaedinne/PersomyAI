#!/usr/bin/env bash
# Restauration d'une sauvegarde pg_dump. OPÉRATION DESTRUCTIVE : remplace le contenu de la base.
# Usage : ./scripts/restore.sh backups/persomy-XXXX.dump
# Une sauvegarde de sécurité de l'état courant est créée automatiquement avant restauration.
set -euo pipefail
cd "$(dirname "$0")/.."

file="${1:-}"
[ -n "${file}" ] && [ -f "${file}" ] || { echo "Usage: $0 <fichier.dump>" >&2; exit 1; }
[ -f .env ] || { echo "Fichier .env introuvable" >&2; exit 1; }
set -a; . ./.env; set +a

echo "ATTENTION : la base '${POSTGRES_DB}' va être remplacée par ${file}."
read -r -p "Tapez RESTAURER pour confirmer : " answer
[ "${answer}" = "RESTAURER" ] || { echo "Annulé."; exit 1; }

./scripts/backup.sh
docker compose stop backend
docker compose exec -T db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner < "${file}"
docker compose start backend
echo "Restauration terminée. Vérifiez : curl -fsS https://api.persomy.com/health/ready"
