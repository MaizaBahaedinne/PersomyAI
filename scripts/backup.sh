#!/usr/bin/env bash
# Sauvegarde logique de PostgreSQL (pg_dump, format custom) dans ./backups.
# Usage (sur le VPS, dans le dossier du projet) : ./scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable" >&2; exit 1; }
set -a; . ./.env; set +a

# Commande Docker : "sudo docker" si l'utilisateur n'est pas dans le groupe docker
# (cas du VPS). Ex. : DOCKER="sudo docker" ./scripts/backup.sh
DOCKER="${DOCKER:-docker}"

umask 077
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="backups/persomy-${stamp}.dump"
tmp="${file}.partial"
trap 'rm -f "${tmp}"' EXIT

# Écriture dans un fichier temporaire : une sauvegarde incomplète n'est jamais conservée.
${DOCKER} compose exec -T db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${tmp}"
[ -s "${tmp}" ] || { echo "Sauvegarde vide : échec" >&2; exit 1; }
# Vérifie que l'archive est lisible par pg_restore avant de la valider.
${DOCKER} compose exec -T db pg_restore --list < "${tmp}" > /dev/null \
  || { echo "Archive illisible : échec" >&2; exit 1; }
mv "${tmp}" "${file}"
echo "Sauvegarde créée : ${file} ($(du -h "${file}" | cut -f1))"

# Rétention : conserve les 14 dernières sauvegardes.
ls -1t backups/persomy-*.dump 2>/dev/null | tail -n +15 | xargs -r rm -f --
