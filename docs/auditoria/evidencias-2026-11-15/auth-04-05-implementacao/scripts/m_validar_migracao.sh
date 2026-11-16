#!/bin/bash
# accounts.0006 — validação pelo comando real migrate, no PG 18.3 DESCARTÁVEL pt_BR. Dados antigos gravados com o código
# ANTERIOR; a migração roda com o código corrigido. Nada aqui toca o banco real.
set -uo pipefail
S=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/ascii
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
A=$S/codigo-anterior
K=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
psql_() { env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke "$@"; }
dj() { local dir=$1 db=$2; shift 2; ( cd $dir && env DEBUG=False SECRET_KEY=$K M_DB=$db PYTHONPATH=$S/pkg:$dir "$@" ); }
estado() {
  psql_ -d $1 -A -c "select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid = 'accounts_user'::regclass and contype in ('c','u') order by 1" \
        -c "select indexname, indexdef from pg_indexes where tablename = 'accounts_user' and indexdef like '%UNIQUE%' order by 1" \
        -c "select count(*) as contas, count(*) filter (where email <> lower(btrim(email))) as fora_do_padrao from accounts_user" \
        -c "select name from django_migrations where app = 'accounts' order by id desc limit 1"
}
for db in m_legado m_valido; do psql_ -d postgres -q -c "drop database if exists $db with (force)" -c "create database $db"; done
psql_ -d postgres -A -c "select datname, datcollate, datctype, datlocprovider, datcollversion from pg_database where datname in ('m_legado','m_valido')"

echo; echo '=== 1. m_legado: esquema e dados com o CÓDIGO ANTERIOR (até accounts.0005)'
dj $A m_legado $P/venv/bin/python manage.py migrate --settings=m_settings --noinput | tail -1
dj $A m_legado env DJANGO_SETTINGS_MODULE=m_settings $P/venv/bin/python $S/scripts/m_dados_legados.py
echo; echo '=== 2. m_legado: migrate com o CÓDIGO CORRIGIDO (deve interromper e mostrar só ids)'
dj $P m_legado $P/venv/bin/python manage.py migrate --settings=m_settings --noinput 2>&1 | grep -E "Applying|MigracaoDeEmailInterrompida|interrompida" | sed 's/^.*MigracaoDeEmailInterrompida: /MigracaoDeEmailInterrompida: /'
estado m_legado
echo; echo '=== 3. m_legado: o dono decide os grupos (SIMULAÇÃO: as contas 4, 5, 7 e 10 recebem e-mail provisório; a 12, não ASCII, também)'
psql_ -d m_legado -c "update accounts_user set email = 'conflito+' || id || '@resolver.invalid' where id in (4, 5, 7, 10, 12)"
dj $P m_legado $P/venv/bin/python manage.py migrate --settings=m_settings --noinput 2>&1 | grep -E "Applying|Interrompida|Error" 
estado m_legado
echo; echo '=== 4. m_legado: reversão (migrate accounts 0005)'
dj $P m_legado $P/venv/bin/python manage.py migrate accounts 0005 --settings=m_settings --noinput 2>&1 | grep -E "Unapplying|Error"
estado m_legado
psql_ -d m_legado -A -c "select id, email from accounts_user where id in (6, 8, 9, 13) order by id"
echo; echo '=== 5. m_valido: dados antigos que a regra normaliza sem colisão'
dj $A m_valido $P/venv/bin/python manage.py migrate --settings=m_settings --noinput | tail -1
dj $A m_valido env DJANGO_SETTINGS_MODULE=m_settings $P/venv/bin/python $S/scripts/m_dados_validos.py
psql_ -d m_valido -A -c "select id, '[' || email || ']' as antes from accounts_user order by id"
dj $P m_valido $P/venv/bin/python manage.py migrate --settings=m_settings --noinput 2>&1 | grep -E "Applying|Error|Interrompida"
psql_ -d m_valido -A -c "select id, '[' || email || ']' as depois from accounts_user order by id"
estado m_valido
echo; echo '=== 6. m_valido: o banco recusa, por fora da aplicação, variação de caixa, espaço e não ASCII'
psql_ -d m_valido -c "update accounts_user set email = 'Pessoa.Dois@exemplo.test' where id = 2" 2>&1 | grep -E "ERRO|ERROR|UPDATE"
psql_ -d m_valido -c "insert into accounts_user (password, is_superuser, is_staff, is_active, date_joined, created_at, updated_at, email, nome, tipo_perfil) values ('!', false, false, true, now(), now(), now(), 'pessoa.dois@exemplo.test ', 'X', 'cliente')" 2>&1 | grep -E "ERRO|ERROR|INSERT"
psql_ -d m_valido -c "insert into accounts_user (password, is_superuser, is_staff, is_active, date_joined, created_at, updated_at, email, nome, tipo_perfil) values ('!', false, false, true, now(), now(), now(), 'x@álfa.test', 'X', 'cliente')" 2>&1 | grep -E "ERRO|ERROR|INSERT"
psql_ -d m_valido -c "insert into accounts_user (password, is_superuser, is_staff, is_active, date_joined, created_at, updated_at, email, nome, tipo_perfil) values ('!', false, false, true, now(), now(), now(), 'pessoa.dois@exemplo.test', 'X', 'cliente')" 2>&1 | grep -E "ERRO|ERROR|INSERT"
echo; echo '=== 7. SQL da migração no PostgreSQL (sqlmigrate accounts 0006)'
dj $P m_valido $P/venv/bin/python manage.py sqlmigrate accounts 0006 --settings=m_settings
