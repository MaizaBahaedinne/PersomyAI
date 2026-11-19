#!/usr/bin/env bash
# Sauvegarde logique de PostgreSQL (pg_dump, format custom) dans ./backups.
# Usage (sur le VPS, dans le dossier du projet) : ./scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable" >&2; exit 1; }
set -a; . ./.env; set +a

mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="backups/persomy-${stamp}.dump"

docker compose exec -T db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${file}"
chmod 600 "${file}"
[ -s "${file}" ] || { echo "Sauvegarde vide : échec" >&2; rm -f "${file}"; exit 1; }
echo "Sauvegarde créée : ${file} ($(du -h "${file}" | cut -f1))"

# Rétention : conserve les 14 dernières sauvegardes.
ls -1t backups/persomy-*.dump 2>/dev/null | tail -n +15 | xargs -r rm -f --
