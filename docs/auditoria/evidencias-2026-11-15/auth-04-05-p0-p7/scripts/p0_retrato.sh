#!/bin/bash
# P0 — retrato do código por LISTA DE INCLUSÃO (backend + fontes do frontend). Sem .env*, dependências, venvs ou ferramentas.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
BD=$1; TS=$2
ARQ="$BD/codigo_$TS.tar.gz"
test ! -e "$ARQ"
cd $P
tar --exclude='*/__pycache__' --exclude='*.pyc' -czf "$ARQ" \
    manage.py requirements.txt config accounts barbershops services appointments \
    frontend/eslint.config.js frontend/.gitignore frontend/index.html frontend/package.json frontend/package-lock.json \
    frontend/public frontend/README.md frontend/src frontend/tests frontend/tsconfig.app.json frontend/tsconfig.json \
    frontend/tsconfig.node.json frontend/vite.config.ts
echo "entradas .env* (esperado 0): $(tar -tzf "$ARQ" | grep -c -E '(^|/)\.env' || true)"
echo "entradas de venv/node_modules/dist/ferramentas (esperado 0): $(tar -tzf "$ARQ" | grep -c -E '(^|/)(\.?venv[^/]*|node_modules|dist|\.claude|\.agents|\.codex|\.impeccable)/' || true)"
echo "topo do retrato: $(tar -tzf "$ARQ" | awk -F/ '{print $1}' | sort -u | tr '\n' ' ')"
( cd "$BD" && sha256sum "codigo_$TS.tar.gz" > "codigo_$TS.tar.gz.sha256" )
stat -c '%a %s %n' "$ARQ" "$ARQ.sha256"
