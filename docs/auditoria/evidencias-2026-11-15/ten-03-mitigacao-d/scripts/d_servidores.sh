#!/bin/bash
# Mitigação D do TEN-03: recria os quatro bancos DESCARTÁVEIS, aplica as migrações, faz o seed fictício (com tokens)
# e sobe quatro APIs com as taxas REAIS:
#   8791 corrigido DEBUG=True | 8792 corrigido DEBUG=False | 8793 anterior DEBUG=True | 8794 anterior DEBUG=False
# Rode este script sozinho (o pkill -f casa com qualquer linha de comando que contenha o texto do runserver).
set -euo pipefail
S=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/d
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
A=$S/codigo-anterior
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
for porta in 8791 8792 8793 8794; do pkill -f "[r]unserver 127.0.0.1:$porta" || true; done; sleep 1
mkdir -p $S/out/api $S/media
subir() {
  local porta=$1 dir=$2 db=$3 debug=$4
  env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "drop database if exists $db with (force)" -c "create database $db"
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K D_DB=$db PYTHONPATH=$S/pkg:$dir $P/venv/bin/python manage.py migrate --settings=d_settings --noinput > $S/out/api/migrate_$db.txt 2>&1 )
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K D_DB=$db PYTHONPATH=$S/pkg:$dir DJANGO_SETTINGS_MODULE=d_settings $P/venv/bin/python $S/scripts/d_seed.py $S/out/api/estado_$porta.json )
  chmod 600 $S/out/api/estado_$porta.json
  env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "alter database $db set log_statement = 'all'"
  ( cd $dir && env DEBUG=$debug SECRET_KEY=$K D_DB=$db PYTHONPATH=$S/pkg:$dir setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:$porta --noreload --settings=d_settings > $S/out/api/runserver_$porta.txt 2>&1 < /dev/null & )
}
subir 8791 $P d_novo_t True
subir 8792 $P d_novo_f False
subir 8793 $A d_ant_t True
subir 8794 $A d_ant_f False
for porta in 8791 8792 8793 8794; do
  for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$porta/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
  echo "api $porta: $c"
done
