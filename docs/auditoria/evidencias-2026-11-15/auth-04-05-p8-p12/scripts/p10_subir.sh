#!/bin/bash
# P10 — sobe a aplicação pelo procedimento do README, a partir do repositório (código conferido), SEM migrate e SEM npm install.
# Backend: venv/bin/python manage.py runserver (127.0.0.1:8000). Frontend: npm run dev (5173). Nada de deploy externo.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
[ "$(ss -ltn | grep -c -E ':(8000|5173) ')" = 0 ] || { echo "INTERROMPIDO: porta 8000 ou 5173 já em uso"; exit 1; }
cd $P
setsid nohup $P/venv/bin/python manage.py runserver > $W/out/p10-backend.txt 2>&1 < /dev/null &
echo $! > $W/out/p10-backend.pid
cd $P/frontend
setsid nohup npm run dev > $W/out/p10-frontend.txt 2>&1 < /dev/null &
echo $! > $W/out/p10-frontend.pid
for i in $(seq 1 40); do b=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/services/ || true); f=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ || true); [ "$b" != 000 ] && [ "$f" != 000 ] && break; sleep 1; done
echo "backend  http://127.0.0.1:8000/api/v1/services/ (sem login): $b   (pid $(cat $W/out/p10-backend.pid))"
echo "frontend http://localhost:5173/: $f   (pid $(cat $W/out/p10-frontend.pid))"
