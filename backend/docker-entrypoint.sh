#!/bin/sh
# Applique les migrations versionnées (additives) puis démarre l'API.
# Toujours sauvegarder la base avant un déploiement : voir docs/DEPLOYMENT.md.
set -e
alembic upgrade head
exec "$@"
