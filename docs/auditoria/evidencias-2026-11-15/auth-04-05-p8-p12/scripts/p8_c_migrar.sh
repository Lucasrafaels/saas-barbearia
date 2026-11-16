#!/bin/bash
# P8 — etapa C: checagem final de processos e execução guardada da accounts.0006 no BANCO REAL. Sem set -x.
set -uo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
cd $P
n=$(pgrep -fa 'manage.py runserver|gunicorn|uvicorn' | grep -v pgrep | wc -l)
echo "== C1 processos da aplicação imediatamente antes: $n"
[ "$n" -eq 0 ] || { echo "INTERROMPIDO: a aplicação está rodando"; exit 2; }
echo "== C2 migração guardada (início $(date '+%F %T'))"
PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' $P/venv/bin/python $W/p8_c_migrar.py 2> $W/out/c-stderr.txt
rc=$?
grep -v -E '^(AVISO|WARNING|DETAIL|DETALHE|HINT|DICA):' $W/out/c-stderr.txt || true
echo "avisos do servidor ao conectar: $(grep -c -E '^(AVISO|WARNING):' $W/out/c-stderr.txt) (versão de ordenação 2.43 × 2.44, DB-02)"
echo "== C2 fim $(date '+%F %T'); código de saída=$rc"
exit $rc
