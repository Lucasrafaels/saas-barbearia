#!/bin/bash
# P8 — etapa B: backup do BANCO REAL imediatamente antes da migração (pg_dump -Fc, sessão somente leitura).
# Diretório novo e exclusivo (0700), arquivo 0600, umask 077, credenciais só por variáveis de ambiente, sem set -x.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
PLANO=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
TS=$(date +%Y%m%d_%H%M%S)
BD=/home/lucasrafael/backups/barberpro/accounts0006_p8_$TS
ARQ=$BD/barbershop_db_${TS}_p8_antes_accounts0006.dump
printf 'TS=%s\nBD=%s\nARQ=%s\n' "$TS" "$BD" "$ARQ" > $W/out/variaveis.txt
test ! -e "$BD"
mkdir -m 700 "$BD"
cd $P
echo "== B1 pg_dump -Fc (início $(date '+%F %T'))"
set +e
$P/venv/bin/python $PLANO/scripts/com_credenciais_da_app.py --somente-leitura -- pg_dump -Fc --no-password -f "$ARQ" 2> $W/out/b-pg_dump-stderr.txt
rc=$?
set -e
grep -v -E '^(AVISO|WARNING|DETALHE|DETAIL|DICA|HINT):' $W/out/b-pg_dump-stderr.txt || true
echo "pg_dump exit=$rc (fim $(date '+%F %T'))"
[ $rc -eq 0 ] || { echo "INTERROMPIDO: pg_dump falhou — a migração NÃO será executada"; exit 1; }
echo "== B2 validação"
[ -s "$ARQ" ] || { echo "INTERROMPIDO: arquivo vazio"; exit 1; }
stat -c 'diretório: permissão=%a %n' "$BD"
stat -c 'arquivo: permissão=%a tamanho=%s bytes %n' "$ARQ"
( cd "$BD" && sha256sum "$(basename "$ARQ")" > "$(basename "$ARQ").sha256" && cat "$(basename "$ARQ").sha256" )
set +e
pg_restore --list "$ARQ" > "$ARQ.lista.txt" 2> $W/out/b-pg_restore-list-stderr.txt
rc=$?
set -e
echo "pg_restore --list exit=$rc; itens: $(grep -c -v '^;' "$ARQ.lista.txt"); TABLE DATA: $(grep -c 'TABLE DATA' "$ARQ.lista.txt")"
[ $rc -eq 0 ] || { echo "INTERROMPIDO: pg_restore --list falhou"; exit 1; }
grep -E '^; *(Archive created|dbname|TOC Entries|Format|Dumped from|Dumped by)' "$ARQ.lista.txt"
grep -q '^;     dbname: barbershop_db$' "$ARQ.lista.txt" || { echo "INTERROMPIDO: o backup não é do barbershop_db"; exit 1; }
grep -q '^;     Dumped from database version: 18.3$' "$ARQ.lista.txt" || { echo "INTERROMPIDO: versão de origem inesperada"; exit 1; }
for t in accounts_user appointments_appointment barbershops_barber barbershops_barbershop django_migrations services_service token_blacklist_blacklistedtoken token_blacklist_outstandingtoken; do
  grep -q "TABLE DATA public $t " "$ARQ.lista.txt" || { echo "INTERROMPIDO: $t ausente do backup"; exit 1; }
done
echo "as 8 tabelas principais estão no backup"
grep -q 'CONSTRAINT public accounts_user accounts_user_email_key' "$ARQ.lista.txt" && echo "restrição accounts_user_email_key presente no backup; accounts_user_email_normalizado presente: $(grep -c 'accounts_user_email_normalizado' "$ARQ.lista.txt")"
diff <(pg_restore --list "$ARQ" | grep -v '^;' | sed -E 's/^[0-9]+; [0-9]+ [0-9]+ //' | sort) <(pg_restore --list /home/lucasrafael/backups/barberpro/accounts0006_20261115_224006/barbershop_db_20261115_224006_antes_accounts0006.dump | grep -v '^;' | sed -E 's/^[0-9]+; [0-9]+ [0-9]+ //' | sort) > /dev/null && echo "lista de objetos idêntica à do backup do ensaio (P3)"
stat -c 'permissão=%a %n' "$ARQ.sha256" "$ARQ.lista.txt"
echo "== B3 contagens no banco real logo depois do backup (somente leitura)"
$P/venv/bin/python $PLANO/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -A -f $PLANO/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/b-contagens-depois.txt
diff $W/out/a5-contagens.txt $W/out/b-contagens-depois.txt && echo "contagens antes e depois do backup: IDÊNTICAS"
echo "backups anteriores intactos: 13/11 $(sha256sum /home/lucasrafael/backups/barberpro/barbershop_db_20261113_220432.dump | cut -c1-16), ensaio $(sha256sum /home/lucasrafael/backups/barberpro/accounts0006_20261115_224006/barbershop_db_20261115_224006_antes_accounts0006.dump | cut -c1-16)"
echo "RESULTADO B: BACKUP CRIADO E VALIDADO"
