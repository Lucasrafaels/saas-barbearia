#!/bin/bash
# AUTH-04/05: sobe a API do código ATUAL (sem alteração) sobre o banco DESCARTÁVEL a45_db, DEBUG=False, porta 8801.
# Rode este script sozinho (o pkill -f casa com qualquer linha de comando que contenha o texto do runserver).
set -euo pipefail
S=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/a45
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
pkill -f "[r]unserver 127.0.0.1:8801" || true; sleep 1
cd $P
env A45_DB=a45_db SECRET_KEY=$K PYTHONPATH=$S/pkg:$P DJANGO_SETTINGS_MODULE=a45_settings $P/venv/bin/python $S/scripts/a45_seed.py $S/out/estado.json
chmod 600 $S/out/estado.json
env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "alter database a45_db set log_statement = 'all'"
env A45_DB=a45_db DEBUG=False SECRET_KEY=$K PYTHONPATH=$S/pkg:$P setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:8801 --noreload --settings=a45_settings > $S/out/runserver_8801.txt 2>&1 < /dev/null &
for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8801/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
echo "api 8801: $c"
