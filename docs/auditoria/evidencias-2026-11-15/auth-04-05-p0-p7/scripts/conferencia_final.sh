#!/bin/bash
# Conferência final no BANCO REAL, somente leitura: o estado deve ser idêntico ao da P2.
set -uo pipefail
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
LER="$P/venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1"
F='^\([0-9]+ (linha|linhas|row|rows)\)$'
cd $P
echo "== conferência final no banco real (somente leitura) $(date '+%F %T')"
$LER -A -f $W/scripts/identidade-somente-leitura.sql 2>/dev/null | grep -E '^barbershop_db\|' || echo "FALHA: identidade não lida"
$LER -f $EVID/sql/01-pre-verificacao-somente-leitura.sql > $W/out/p-final-pre-verificacao.txt 2>/dev/null; echo "01 exit=$?"
diff <(sed -n '/== 2\. Migrações/,/== 5\./p' $W/out/p2-2-pre-verificacao-plano.txt | grep -v -E "$F") <(sed -n '/== 2\. Migrações/,/== 5\./p' $W/out/p-final-pre-verificacao.txt | grep -v -E "$F") \
  && echo "migrações, restrições, índices e regra: IDÊNTICOS à P2 (accounts.0006 ausente; nenhuma restrição nova)"
$LER -A -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/p-final-contagens.txt
diff <(grep -E '\|' $W/out/p2-4-contagens.txt) $W/out/p-final-contagens.txt && echo "contagens: IDÊNTICAS à P2"
