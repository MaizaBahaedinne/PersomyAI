#!/usr/bin/env bash
# Mise a jour VPS Persomy v2 : pull, build, up, TWO_FACTOR_KEY, verifications.
# Usage:
#   APP_DIR=/opt/persomy-v2 DOCKER="sudo docker" ./scripts/update-vps-2fa.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/persomy-v2}"
DOCKER="${DOCKER:-sudo docker}"
COMPOSE="${DOCKER} compose"

log() {
  printf "\n== %s ==\n" "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Commande requise introuvable: $1" >&2
    exit 1
  }
}

require_cmd git

if [[ ! -d "$APP_DIR" ]]; then
  echo "Dossier introuvable: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Fichier .env introuvable dans $APP_DIR" >&2
  exit 1
fi
chmod 600 .env

# Charge les variables pour les verifications psql
set -a
. ./.env
set +a

if [[ -z "${POSTGRES_USER:-}" || -z "${POSTGRES_DB:-}" ]]; then
  echo "POSTGRES_USER/POSTGRES_DB absents de .env" >&2
  exit 1
fi

log "1) Mise a jour Git"
git fetch origin
git pull --ff-only

log "2) Build + demarrage"
${COMPOSE} build
${COMPOSE} up -d

log "3) TWO_FACTOR_KEY"
current_key="$(grep -E '^TWO_FACTOR_KEY=' .env | cut -d'=' -f2- || true)"
if [[ -z "$current_key" ]]; then
  echo "TWO_FACTOR_KEY absente: generation..."
  key="$(${COMPOSE} exec -T backend python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  if grep -q '^TWO_FACTOR_KEY=' .env; then
    sed -i.bak "s|^TWO_FACTOR_KEY=.*|TWO_FACTOR_KEY=${key}|" .env
  else
    printf '\nTWO_FACTOR_KEY=%s\n' "$key" >> .env
  fi
  chmod 600 .env
  rm -f .env.bak
  echo "TWO_FACTOR_KEY ajoutee dans .env"
  echo "Recreation du backend pour charger la variable"
  ${COMPOSE} up -d backend
else
  echo "TWO_FACTOR_KEY deja definie"
fi

log "4) Verifier migration (attendu: 0004)"
version="$(${COMPOSE} exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc 'select version_num from alembic_version;')"
echo "alembic_version=$version"
if [[ "$version" != "0004" ]]; then
  echo "ATTENTION: version Alembic inattendue (attendu: 0004)" >&2
fi

log "5) Sante backend"
${COMPOSE} exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"

log "6) Controle ports 80/443 (ancien caddy)"
sudo ss -ltnp | grep -E ':80 |:443 ' || true
${DOCKER} ps --format 'table {{.Names}}\t{{.Ports}}' | grep -E '80->|443->|caddy' || true

log "Termine"
echo "Active ensuite la 2FA dans l'UI (Parametres > Securite) pour chaque admin."
#!/usr/bin/env bash
# Mise a jour VPS Persomy v2 : pull, build, up, TWO_FACTOR_KEY, verifications.
# Usage:
#   APP_DIR=/opt/persomy-v2 DOCKER="sudo docker" ./scripts/update-vps-2fa.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/persomy-v2}"
DOCKER="${DOCKER:-sudo docker}"
COMPOSE="${DOCKER} compose"

log() {
  printf "\n== %s ==\n" "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Commande requise introuvable: $1" >&2
    exit 1
  }
}

require_cmd git

if [[ ! -d "$APP_DIR" ]]; then
  echo "Dossier introuvable: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Fichier .env introuvable dans $APP_DIR" >&2
  exit 1
fi
chmod 600 .env

# Charge les variables pour les verifications psql
set -a
. ./.env
set +a

if [[ -z "${POSTGRES_USER:-}" || -z "${POSTGRES_DB:-}" ]]; then
  echo "POSTGRES_USER/POSTGRES_DB absents de .env" >&2
  exit 1
fi

log "1) Mise a jour Git"
git fetch origin
git pull --ff-only

log "2) Build + demarrage"
$COMPOSE build
$COMPOSE up -d

log "3) TWO_FACTOR_KEY"
current_key="$(grep -E '^TWO_FACTOR_KEY=' .env | cut -d'=' -f2- || true)"
if [[ -z "$current_key" ]]; then
  echo "TWO_FACTOR_KEY absente: generation..."
  key="$($COMPOSE exec -T backend python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  if grep -q '^TWO_FACTOR_KEY=' .env; then
    sed -i.bak "s|^TWO_FACTOR_KEY=.*|TWO_FACTOR_KEY=${key}|" .env
  else
    printf '\nTWO_FACTOR_KEY=%s\n' "$key" >> .env
  fi
  chmod 600 .env
  rm -f .env.bak
  echo "TWO_FACTOR_KEY ajoutee dans .env"
  echo "Recreation du backend pour charger la variable"
  $COMPOSE up -d backend
else
  echo "TWO_FACTOR_KEY deja definie"
fi

log "4) Verifier migration (attendu: 0004)"
version="$($COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc 'select version_num from alembic_version;')"
echo "alembic_version=$version"
if [[ "$version" != "0004" ]]; then
  echo "ATTENTION: version Alembic inattendue (attendu: 0004)" >&2
fi

log "5) Sante backend"
$COMPOSE exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"

log "6) Controle ports 80/443 (ancien caddy)"
sudo ss -ltnp | grep -E ':80 |:443 ' || true
$DOCKER ps --format 'table {{.Names}}\t{{.Ports}}' | grep -E '80->|443->|caddy' || true

log "Termine"
echo "Active ensuite la 2FA dans l'UI (Parametres > Securite) pour chaque admin."
