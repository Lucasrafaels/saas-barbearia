#!/bin/bash
# TEN-02: recria o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432) com log de todos os comandos SQL,
# aplica as migrações, roda o seed fictício e sobe cinco APIs isoladas:
#   8767 corrigido DEBUG=True | 8768 corrigido DEBUG=False | 8769 anterior DEBUG=True | 8770 anterior DEBUG=False
#   8773 código da auditoria (HEAD), DEBUG=True, para referência do comportamento original
# "Anterior" = árvore com a contenção e a correção estrutural do TEN-01, antes desta etapa.
set -euo pipefail
I=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/1849e68b-a8bd-402f-b975-c50f853b5427/scratchpad/iso
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
A=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/1849e68b-a8bd-402f-b975-c50f853b5427/scratchpad/ten02/codigo-anterior
H=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/1849e68b-a8bd-402f-b975-c50f853b5427/scratchpad/ten02/codigo-auditoria
for porta in 8767 8768 8769 8770 8773; do pkill -f "[r]unserver 127.0.0.1:$porta" || true; done; sleep 1
env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "drop database if exists iso_db with (force)" -c "create database iso_db"
rm -rf $I/media && mkdir -p $I/media $I/evidencias-t2
cd $P
PYTHONPATH=$I/pkg:$P venv/bin/python manage.py migrate --settings=iso_settings --noinput > $I/evidencias-t2/migrate.log 2>&1
PYTHONPATH=$I/pkg:$P DJANGO_SETTINGS_MODULE=iso_settings venv/bin/python $I/scripts/seed.py $I/evidencias-t2/estado_seed.json > /dev/null
chmod 600 $I/evidencias-t2/estado_seed.json
# Log de todos os comandos só deste banco, depois do seed.
env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -q -c "alter database iso_db set log_statement = 'all'"
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
subir() {
  local porta=$1 dir=$2 cfg=$3; shift 3
  ( cd $dir && env "$@" PYTHONPATH=$I/pkg:$dir setsid nohup $P/venv/bin/python manage.py runserver 127.0.0.1:$porta --noreload --settings=$cfg > $I/evidencias-t2/api_$porta.log 2>&1 < /dev/null & )
}
subir 8767 $P iso_settings
subir 8768 $P iso_prod_settings DEBUG=False SECURE_SSL_REDIRECT=False
subir 8769 $A iso_settings DEBUG=True SECRET_KEY=$K
subir 8770 $A iso_prod_settings DEBUG=False SECURE_SSL_REDIRECT=False SECRET_KEY=$K
subir 8773 $H iso_settings DEBUG=True SECRET_KEY=$K
for porta in 8767 8768 8769 8770 8773; do
  for i in $(seq 1 30); do c=$(curl -s -o /dev/null -w "%{http_code}" -H 'Accept: application/json' http://127.0.0.1:$porta/api/v1/services/ || true); [ "$c" != 000 ] && break; sleep 1; done
  echo "api $porta: $c"
done
