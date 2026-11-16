#!/bin/bash
# Fotografa os contadores de escrita do banco real (somente leitura) e compara com a linha de base S0.
set -uo pipefail
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1; ROTULO=$2
cd $P
sleep 3   # os contadores do PostgreSQL são publicados em até ~1 s após o fim de cada transação
$P/venv/bin/python $P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -A -f $W/estatisticas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/estatisticas-$ROTULO.txt
diff $W/out/estatisticas-s0-depois-p9.txt $W/out/estatisticas-$ROTULO.txt > $W/out/estatisticas-diff-$ROTULO.txt && echo "contadores de inserção/atualização/exclusão ($ROTULO): IDÊNTICOS à linha de base — nenhuma escrita" || { echo "CONTADORES MUDARAM ($ROTULO):"; cat $W/out/estatisticas-diff-$ROTULO.txt; }
