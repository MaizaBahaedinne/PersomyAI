#!/usr/bin/env bash
# Benchmark rapide de modèles Ollama pour Persomy AI (latence + tokens), côté VPS.
# Usage:
#   DOCKER="sudo docker" ./scripts/benchmark-ollama-models.sh
#   DOCKER="sudo docker" ./scripts/benchmark-ollama-models.sh qwen2.5:3b-instruct qwen2.5:7b-instruct
set -euo pipefail

cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable (copier .env.example)" >&2; exit 1; }

set -a
. ./.env
set +a

DOCKER_CMD="${DOCKER:-docker}"
BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
PROMPT="Résume en 3 points concrets comment améliorer une prospection B2B cette semaine."
SYSTEM="Tu es un assistant opérationnel orienté exécution business."
RUNS=3
TIMEOUT_SECONDS="${OLLAMA_BENCH_TIMEOUT_SECONDS:-180}"

if [ "$#" -gt 0 ]; then
  MODELS=("$@")
else
  MODELS=(
    "qwen2.5:3b-instruct"
    "qwen2.5:7b-instruct"
    "llama3.1:8b"
  )
fi

echo "== Validation docker compose =="
${DOCKER_CMD} compose config -q

echo "== Démarrage des services ollama + backend =="
${DOCKER_CMD} compose up -d ollama backend

echo "== Benchmark (base_url=${BASE_URL}, runs=${RUNS}, timeout=${TIMEOUT_SECONDS}s) =="
printf "%-24s | %-14s | %-12s | %-12s | %s\n" "MODEL" "AVG_MS" "TOKENS_IN" "TOKENS_OUT" "SAMPLE"
printf "%.0s-" {1..110}; echo

for model in "${MODELS[@]}"; do
  echo "[info] pull ${model}" >&2
  ${DOCKER_CMD} compose exec -T ollama ollama pull "${model}" >/dev/null

  echo "[info] benchmark ${model} (${RUNS} runs)" >&2

    line="$(${DOCKER_CMD} compose exec -T backend python -c "
  import json, socket, sys, time, traceback, urllib.error, urllib.request
base='${BASE_URL}'.rstrip('/')
model='${model}'
runs=${RUNS}
timeout=${TIMEOUT_SECONDS}
system='''${SYSTEM}'''
prompt='''${PROMPT}'''

ms=[]
tin=[]
tout=[]
sample=''
  try:
    for i in range(runs):
      print(f'[run {i+1}/{runs}] {model}', file=sys.stderr, flush=True)
      payload={
        'model': model,
        'system': system,
        'prompt': prompt,
        'stream': False,
      }
      req=urllib.request.Request(
        f'{base}/api/generate',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type':'application/json'},
        method='POST'
      )
      t0=time.perf_counter()
      with urllib.request.urlopen(req, timeout=timeout) as r:
        body=json.loads(r.read().decode('utf-8'))
      dt=(time.perf_counter()-t0)*1000
      ms.append(dt)
      tin.append(int(body.get('prompt_eval_count') or 0))
      tout.append(int(body.get('eval_count') or 0))
      if not sample:
        sample=(body.get('response') or '').strip().replace('\n',' ')[:70]

    avg_ms=round(sum(ms)/len(ms),1)
    avg_in=round(sum(tin)/len(tin),1)
    avg_out=round(sum(tout)/len(tout),1)
    print(f'OK|{model}|{avg_ms}|{avg_in}|{avg_out}|{sample}')
  except urllib.error.HTTPError as exc:
    print(f'ERR|{model}|http_{exc.code}|{str(exc)[:120]}')
  except urllib.error.URLError as exc:
    print(f'ERR|{model}|url_error|{str(exc.reason)[:120]}')
  except (socket.timeout, TimeoutError) as exc:
    print(f'ERR|{model}|timeout|{str(exc)[:120]}')
  except Exception as exc:
    print(f'ERR|{model}|exception|{type(exc).__name__}: {str(exc)[:120]}')
  " || true)"

  if [ -z "$line" ]; then
    printf "%-24s | %-14s | %-12s | %-12s | %s\n" "$model" "ERROR" "-" "-" "Echec appel generate"
    continue
  fi

  IFS='|' read -r status m a b c d <<< "$line"
  if [ "$status" = "OK" ]; then
    printf "%-24s | %-14s | %-12s | %-12s | %s\n" "$m" "$a" "$b" "$c" "$d"
  else
    printf "%-24s | %-14s | %-12s | %-12s | %s\n" "$m" "ERROR" "-" "-" "${a}: ${b}"
  fi
done

echo
cat <<EOF
Conseil d'usage:
- Prends le modèle avec le meilleur compromis AVG_MS / qualité perçue.
- Pour l'appliquer dans Persomy AI:
  1) Modifier OLLAMA_MODEL dans .env
  2) ${DOCKER_CMD} compose up -d backend
EOF
