#!/bin/bash
# P6 — ensaio da accounts.0006 na CÓPIA restaurada (ensaio_restaurado, 127.0.0.1:55432), com a CÓPIA isolada do código.
# SECRET_KEY aleatória (nenhum token do ensaio vale na aplicação real); e-mail locmem (ensaio_settings). Nada toca o banco real.
set -uo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))') DEBUG=False PYTHONPATH=$EVID/scripts:$W/codigo
D() { env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d ensaio_restaurado "$@"; }
MG() { ( cd $W/codigo && $P/venv/bin/python manage.py "$@" --settings=ensaio_settings ); }
emails_hash() { D -At -c "select md5(string_agg(id::text || ':' || email, ',' order by id)) from accounts_user"; }
parar() { echo "INTERROMPIDO: $1"; exit 1; }
echo "== P6.0 a aplicação do ensaio aponta para a cópia descartável"
( cd $W/codigo && $P/venv/bin/python -c "
import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'ensaio_settings'; django.setup()
from django.conf import settings as s; d = s.DATABASES['default']
print('banco', d['NAME'], 'em', d['HOST'] + ':' + str(d['PORT']), '| e-mail', s.EMAIL_BACKEND.rsplit('.', 2)[-2], '| DEBUG', s.DEBUG)
assert d['NAME'] == 'ensaio_restaurado' and d['PORT'] == '55432' and d['HOST'] == '127.0.0.1'
assert s.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend'
" 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning" ) || parar "settings do ensaio"
echo "== P6.1 regra exata pela própria função da migração (forma_canonica), sobre os e-mails da cópia, sem imprimi-los"
( cd $W/codigo && $P/venv/bin/python -c "
import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'ensaio_settings'; django.setup()
from collections import Counter; from django.db import connection
from accounts.emails import forma_canonica
with connection.cursor() as c:
    c.execute('select id, email from accounts_user order by id'); linhas = c.fetchall()
can = {i: forma_canonica(e) for i, e in linhas}
fora = [i for i, v in can.items() if v is None]; mudam = [i for i, e in linhas if can[i] is not None and can[i] != e]
grupos = [k for k, n in Counter(v for v in can.values() if v).items() if n > 1]
print(f'contas={len(linhas)} fora_da_regra={len(fora)} {fora} a_normalizar={len(mudam)} {mudam} grupos_de_colisao={len(grupos)}')
" 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning" )
echo "== P6.2 migrate --plan na cópia (esperado: só accounts.0006)"
MG migrate --plan 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"
antes=$(emails_hash)
echo "== P6.3 migrate accounts 0006 na cópia"
PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' MG migrate accounts 0006 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"; [ ${PIPESTATUS[0]} -eq 0 ] || parar "migração falhou na cópia"
echo "== P6.4 pós-verificação na cópia"
D -f $EVID/sql/02-pos-verificacao-somente-leitura.sql 2>&1
echo "e-mails inalterados pela migração (nada a normalizar): $([ "$antes" = "$(emails_hash)" ] && echo sim || echo NÃO)"
echo "== P6.5 coerência: migrate --check (sem pendências) e makemigrations --check (modelos = migrações)"
MG migrate --check 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"; echo "migrate --check exit=${PIPESTATUS[0]}"
MG makemigrations --check --dry-run 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"; echo "makemigrations --check exit=${PIPESTATUS[0]}"
echo "== P6.6 reversão na cópia (migrate accounts 0005)"
PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' MG migrate accounts 0005 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"; [ ${PIPESTATUS[0]} -eq 0 ] || parar "reversão falhou"
D -A -c "select count(*) filter (where conname in ('accounts_user_email_normalizado')) as check_presente, (select count(*) from pg_indexes where indexname = 'accounts_user_email_lower_unico') as indice_presente, (select count(*) from pg_constraint where conname = 'accounts_user_email_key') as unique_original from pg_constraint where conrelid = 'accounts_user'::regclass"
D -At -c "select 'última accounts: ' || max(name) from django_migrations where app = 'accounts'"
echo "e-mails inalterados pela reversão: $([ "$antes" = "$(emails_hash)" ] && echo sim || echo NÃO)"
echo "== P6.7 reaplicação para os testes de fumaça"
PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' MG migrate accounts 0006 2>&1 | grep -v -E "\.env doesn't exist|warnings.warn|UserWarning"; [ ${PIPESTATUS[0]} -eq 0 ] || parar "reaplicação falhou"
D -f $EVID/sql/02-pos-verificacao-somente-leitura.sql 2>&1 | sed -n '/== 2/,/== 4/p'
