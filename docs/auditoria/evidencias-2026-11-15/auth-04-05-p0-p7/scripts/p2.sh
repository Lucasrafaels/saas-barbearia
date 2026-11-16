#!/bin/bash
# P2 — pré-verificação no BANCO REAL, somente leitura (sessão default_transaction_read_only=on + BEGIN READ ONLY + ROLLBACK).
# Credenciais só pelo com_credenciais_da_app.py (variáveis de ambiente do processo filho; nunca impressas). Sem set -x.
set -uo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
LER="$P/venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1"
cd $P
echo "== P2.1 identidade do banco conectado"
$LER -A -f $W/scripts/identidade-somente-leitura.sql > $W/out/p2-1-identidade.txt 2>&1; rc=$?
cat $W/out/p2-1-identidade.txt
linha=$(grep -E '^barbershop_db\|' $W/out/p2-1-identidade.txt || true)
IFS='|' read -r banco confere versao endereco porta usuario tro sro collate ctype prov collv <<< "$linha"
if [ $rc -ne 0 ] || [ "$confere" != t ] || [ "$versao" != 18.3 ] || [ "$porta" != 5432 ] || [ "$usuario" != t ] || [ "$sro" != on ] \
   || [ "$ctype" != pt_BR.UTF-8 ] || [ "$prov" != c ] || { [ "$endereco" != ::1 ] && [ "$endereco" != 127.0.0.1 ]; }; then
  echo "INTERROMPIDO: identidade diverge do esperado"; exit 1
fi
echo "IDENTIDADE CONFIRMADA: barbershop_db, PostgreSQL 18.3, $endereco:5432, usuário esperado, sessão somente leitura, $ctype (libc)"
echo; echo "== P2.2 pré-verificação do plano (01-pre-verificacao-somente-leitura.sql)"
$LER -f $EVID/sql/01-pre-verificacao-somente-leitura.sql > $W/out/p2-2-pre-verificacao-plano.txt 2>&1; echo "exit=$?" >> $W/out/p2-2-pre-verificacao-plano.txt
cat $W/out/p2-2-pre-verificacao-plano.txt
echo; echo "== P2.3 regra exata da migração (pre-verificacao-regra-exata-somente-leitura.sql)"
$LER -f $W/scripts/pre-verificacao-regra-exata-somente-leitura.sql > $W/out/p2-3-regra-exata.txt 2>&1; echo "exit=$?" >> $W/out/p2-3-regra-exata.txt
cat $W/out/p2-3-regra-exata.txt
echo; echo "== P2.4 contagens (03-contagem-de-linhas-somente-leitura.sql)"
$LER -A -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql > $W/out/p2-4-contagens.txt 2>&1; echo "exit=$?" >> $W/out/p2-4-contagens.txt
cat $W/out/p2-4-contagens.txt
echo; echo "== P2.5 estado das migrações pelo Django (sessão somente leitura)"
{ PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000' $P/venv/bin/python manage.py showmigrations accounts barbershops 2>&1; echo "exit=$?";
  echo '--- migrate --plan'; PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000' $P/venv/bin/python manage.py migrate --plan 2>&1; echo "exit=$?"; } > $W/out/p2-5-migracoes.txt
cat $W/out/p2-5-migracoes.txt
