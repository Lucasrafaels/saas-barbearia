#!/bin/bash
# TEN-03: sobe a API do código ATUAL (sem alteração) sobre o banco DESCARTÁVEL t3_db, com DEBUG=False,
# e liga log_statement='all' só neste banco. Nunca usa o .env para o banco (DATABASES vem de t3_settings).
set -euo pipefail
S=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/t3
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
pkill -f "[r]unserver 127.0.0.1:8781" || true; sleep 1
env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "alter database t3_db set log_statement = 'all'"
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
( cd $P && env DEBUG=False SECRET_KEY=$K PYTHONPATH=$S/pkg:$P setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:8781 --noreload --settings=t3_settings > $S/out/api_8781.txt 2>&1 < /dev/null & )
for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8781/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
echo "api 8781: $c"
