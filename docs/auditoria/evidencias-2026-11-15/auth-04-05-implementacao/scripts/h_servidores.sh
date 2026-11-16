#!/bin/bash
# AUTH-04/05: três APIs sobre bancos DESCARTÁVEIS (PG 18.3 pt_BR): 8811 corrigido DEBUG=False | 8812 corrigido DEBUG=True |
# 8813 anterior DEBUG=False. Rode sozinho (o pkill -f casa com qualquer linha que contenha o texto do runserver).
set -euo pipefail
S=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/ascii
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
A=$S/codigo-anterior
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
for porta in 8811 8812 8813; do pkill -f "[r]unserver 127.0.0.1:$porta" || true; done; sleep 1
mkdir -p $S/out/api $S/media
subir() {
  local porta=$1 dir=$2 db=$3 debug=$4
  mkdir -p $S/out/mail_$porta
  env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "drop database if exists $db with (force)" -c "create database $db"
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K H_DB=$db H_MAIL=$S/out/mail_$porta PYTHONPATH=$S/pkg:$dir $P/venv/bin/python manage.py migrate --settings=h_settings --noinput > $S/out/api/migrate_$db.txt 2>&1 )
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K H_DB=$db H_MAIL=$S/out/mail_$porta PYTHONPATH=$S/pkg:$dir DJANGO_SETTINGS_MODULE=h_settings $P/venv/bin/python $S/scripts/h_seed.py $S/out/api/estado_$porta.json )
  chmod 600 $S/out/api/estado_$porta.json
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K H_DB=$db H_MAIL=$S/out/mail_$porta PYTHONPATH=$S/pkg:$dir setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:$porta --noreload --settings=h_settings > $S/out/api/runserver_$porta.txt 2>&1 < /dev/null & )
}
subir 8811 $P h_novo_f False
subir 8812 $P h_novo_t True
subir 8813 $A h_ant_f False
for porta in 8811 8812 8813; do
  for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$porta/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
  echo "api $porta: $c"
done
