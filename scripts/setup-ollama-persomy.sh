#!/usr/bin/env bash
# Configure Ollama sur le VPS et relie Persomy AI au provider local.
# Idempotent : peut être relancé sans casser l'existant.
set -euo pipefail

cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }

set -a
. ./.env
set +a

DOCKER_CMD="${DOCKER:-docker}"
MODEL="${1:-${OLLAMA_MODEL:-qwen2.5:3b-instruct}}"

upsert_env() {
  key="$1"
  value="$2"
  if grep -qE "^${key}=" .env; then
    sed -i.bak "s#^${key}=.*#${key}=${value}#" .env
  else
    printf '\n%s=%s\n' "$key" "$value" >> .env
  fi
}

echo "== Validation docker compose =="
${DOCKER_CMD} compose config -q

echo "== Configuration provider Ollama dans .env =="
upsert_env "AI_PROVIDER" "ollama"
upsert_env "OLLAMA_BASE_URL" "http://ollama:11434"
upsert_env "OLLAMA_MODEL" "${MODEL}"

# Recharge les valeurs après mise à jour
set -a
. ./.env
set +a

echo "== Démarrage Ollama + backend =="
${DOCKER_CMD} compose up -d ollama backend

echo "== Préchargement du modèle: ${OLLAMA_MODEL} =="
${DOCKER_CMD} compose exec -T ollama ollama pull "${OLLAMA_MODEL}"

echo "== Rebuild backend (prise en compte du provider Ollama) =="
${DOCKER_CMD} compose build backend

echo "== Redémarrage backend avec la config provider =="
${DOCKER_CMD} compose up -d backend

echo "== Vérification connectivité backend -> ollama =="
${DOCKER_CMD} compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://ollama:11434/api/tags', timeout=20).status)"

echo "== Vérification provider Persomy AI =="
${DOCKER_CMD} compose exec -T backend python -c "from app.modules.orchestration import providers; print(providers.provider_info())"

echo "Terminé. Provider actif: ollama | Modèle: ${OLLAMA_MODEL}"
