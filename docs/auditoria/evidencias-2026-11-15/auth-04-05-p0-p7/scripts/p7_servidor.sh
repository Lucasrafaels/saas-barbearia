#!/bin/bash
# P7 — sobe a API da CÓPIA do código sobre a CÓPIA restaurada (127.0.0.1:8899), DEBUG=False, SECRET_KEY aleatória.
set -euo pipefail
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
cd $W/codigo
env SECRET_KEY=$K DEBUG=False PYTHONPATH=$W/pkg:$EVID/scripts:$W/codigo setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:8899 --noreload --settings=ensaio_fumaca_settings > $W/out/p7-runserver.txt 2>&1 < /dev/null &
echo $! > $W/out/p7-runserver.pid
for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8899/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
echo "API do ensaio em 127.0.0.1:8899: $c (pid $(cat $W/out/p7-runserver.pid))"
