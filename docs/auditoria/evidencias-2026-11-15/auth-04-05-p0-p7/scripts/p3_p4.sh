#!/bin/bash
# P3 e P4 — backup novo do BANCO REAL (pg_dump -Fc, sessão somente leitura) e verificação do arquivo.
# umask 077; credenciais só por variáveis de ambiente (com_credenciais_da_app.py); sem set -x; nada vai para a rede.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
source <(grep -E '^(TS|BD)=' $W/out/variaveis.txt)
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
ARQ="$BD/barbershop_db_${TS}_antes_accounts0006.dump"
echo "ARQ=$ARQ" >> $W/out/variaveis.txt
test -d "$BD" && [ "$(stat -c %a "$BD")" = 700 ]
test ! -e "$ARQ"
cd $P
echo "== P3 pg_dump -Fc (início $(date '+%F %T'))"
set +e
$P/venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- pg_dump -Fc --no-password -f "$ARQ" 2> $W/out/p3-pg_dump-stderr.txt
rc=$?
set -e
grep -v -E '^(AVISO|WARNING|DETALHE|DETAIL|DICA|HINT):' $W/out/p3-pg_dump-stderr.txt || true
echo "pg_dump exit=$rc (fim $(date '+%F %T'))"
[ $rc -eq 0 ] || { echo "INTERROMPIDO: pg_dump falhou"; exit 1; }
echo "== P4 integridade"
[ -s "$ARQ" ] || { echo "INTERROMPIDO: arquivo vazio"; exit 1; }
stat -c 'permissão=%a tamanho=%s bytes arquivo=%n' "$ARQ"
( cd "$BD" && sha256sum "$(basename "$ARQ")" > "$(basename "$ARQ").sha256" && cat "$(basename "$ARQ").sha256" )
set +e
pg_restore --list "$ARQ" > "$ARQ.lista.txt" 2> $W/out/p4-pg_restore-list-stderr.txt
rc=$?
set -e
echo "pg_restore --list exit=$rc; itens no índice: $(grep -c -v '^;' "$ARQ.lista.txt"); TABLE DATA: $(grep -c 'TABLE DATA' "$ARQ.lista.txt")"
[ $rc -eq 0 ] || { echo "INTERROMPIDO: pg_restore --list falhou"; exit 1; }
grep -q 'TABLE DATA public accounts_user ' "$ARQ.lista.txt" || { echo "INTERROMPIDO: accounts_user ausente do backup"; exit 1; }
for t in accounts_user appointments_appointment barbershops_barber barbershops_barbershop django_migrations services_service token_blacklist_blacklistedtoken token_blacklist_outstandingtoken; do
  grep -q "TABLE DATA public $t " "$ARQ.lista.txt" && echo "  presente: $t" || { echo "INTERROMPIDO: $t ausente"; exit 1; }
done
head -12 "$ARQ.lista.txt" | grep -E '^;' | grep -v -i -E 'owner|user' 
stat -c 'permissão=%a %n' "$ARQ.sha256" "$ARQ.lista.txt"
echo "== contagens no banco real logo DEPOIS do backup (somente leitura), para comparar com P2.4"
$P/venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -A -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/p4-contagens-depois.txt
diff <(grep -E '\|' $W/out/p2-4-contagens.txt) $W/out/p4-contagens-depois.txt && echo "contagens antes e depois do backup: IDÊNTICAS"
echo "backup de 13/11 intacto: $(sha256sum /home/lucasrafael/backups/barberpro/barbershop_db_20261113_220432.dump | cut -c1-16)"
