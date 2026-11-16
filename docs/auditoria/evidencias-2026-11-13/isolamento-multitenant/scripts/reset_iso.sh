#!/bin/bash
# Recria o banco DESCARTÁVEL iso_db (127.0.0.1:55432), aplica as migrations, roda o seed fictício e reinicia a API isolada (8767).
set -euo pipefail
I=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/61af1f5c-5709-41df-b16b-b2a7a28636f3/scratchpad/iso
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
[ -f $I/api.pid ] && kill -- -$(ps -o pgid= -p $(cat $I/api.pid) | tr -d ' ') 2>/dev/null || true; sleep 1
env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "drop database if exists iso_db with (force)" -c "create database iso_db"
rm -rf $I/media && mkdir -p $I/media
cd $P && source venv/bin/activate
export PYTHONPATH=$I/pkg:$P DJANGO_SETTINGS_MODULE=iso_settings
python manage.py migrate --settings=iso_settings --noinput > $I/evidencias/migrate.log 2>&1
python $I/scripts/seed.py $I/evidencias/estado_seed.json; chmod 600 $I/evidencias/estado_seed.json
setsid nohup python manage.py runserver 127.0.0.1:8767 --noreload --settings=iso_settings > $I/evidencias/api_isolada.log 2>&1 < /dev/null & echo $! > $I/api.pid
for i in $(seq 1 20); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8767/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done; echo "api 8767: $c"
