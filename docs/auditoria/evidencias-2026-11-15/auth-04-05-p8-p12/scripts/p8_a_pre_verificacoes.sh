#!/bin/bash
# P8 — etapa A: pré-verificações no BANCO REAL, somente leitura, comparadas com a P2 do ensaio P0–P7 (seção 33).
# Credenciais só por variáveis de ambiente (com_credenciais_da_app.py). Sem set -x.
set -uo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
PLANO=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
E7=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-p0-p7
LER="$P/venv/bin/python $PLANO/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1"
F='^\([0-9]+ (linha|linhas|row|rows)\)$'
divergencias=0
diverge() { echo "DIVERGÊNCIA: $1"; divergencias=$((divergencias+1)); }
cd $P
echo "== A1 identidade configurada (antes de conectar)"
$P/venv/bin/python $E7/scripts/identidade_configurada.py 2>&1 || diverge "identidade configurada"
echo "== A2 identidade do banco conectado"
linha=$($LER -A -f $E7/scripts/identidade-somente-leitura.sql 2>/dev/null | grep -E '^barbershop_db\|')
echo "$linha"
[ "$linha" = "$(grep -E '^barbershop_db\|' $E7/saidas/p2-1-identidade.txt)" ] && echo "idêntica à P2 do ensaio: barbershop_db | 18.3 | ::1:5432 | usuário confere | somente leitura | pt_BR.UTF-8 | libc | 2.43" || diverge "identidade conectada"
echo "   não é o banco antigo 'barbershop' (nome) nem o Docker (porta 5433, PostgreSQL 16): banco=barbershop_db, porta=5432, versão=18.3"
echo "== A3 pré-verificação do plano (migrações, restrições, índices, regra do CHECK, sessões, travas)"
$LER -f $PLANO/sql/01-pre-verificacao-somente-leitura.sql > $W/out/a3-pre-verificacao.txt 2>/dev/null || diverge "01 falhou"
sed -n '/== 2\. Migrações/,$p' $W/out/a3-pre-verificacao.txt
diff <(sed -n '/== 2\. Migrações/,/== 5\./p' $E7/saidas/p2-2-pre-verificacao-plano.txt | grep -v -E "$F") <(sed -n '/== 2\. Migrações/,/== 5\./p' $W/out/a3-pre-verificacao.txt | grep -v -E "$F") > /dev/null \
  && echo "migrações, restrição accounts_user_email_key, índices e regra do CHECK: IDÊNTICOS à P2" || diverge "migrações/restrições/índices/regra"
grep -A3 '== 5\.' $W/out/a3-pre-verificacao.txt | grep -q -E '^\(0 (linha|rows)\)' && echo "sessões de outros: nenhuma" || diverge "há outras sessões"
grep -A3 '== 6\.' $W/out/a3-pre-verificacao.txt | grep -q -E '^\(0 (linha|rows)\)' && echo "travas em accounts_user: nenhuma" || diverge "há travas"
echo "== A4 regra EXATA da migração (forma_canonica em SQL, equivalência provada na seção 33)"
$LER -f $E7/scripts/pre-verificacao-regra-exata-somente-leitura.sql > $W/out/a4-regra-exata.txt 2>/dev/null || diverge "regra exata falhou"
sed -n '/== R1/,$p' $W/out/a4-regra-exata.txt
diff <(sed -n '/== R1/,$p' $E7/saidas/p2-3-regra-exata.txt | grep -v -E '^exit=' | grep -v -E "$F") <(sed -n '/== R1/,$p' $W/out/a4-regra-exata.txt | grep -v -E "$F") > /dev/null \
  && echo "regra exata: IDÊNTICA à P2 (8 contas, 8 canônicas, 0 a normalizar, 0 fora, 0 colisões)" || diverge "regra exata"
echo "== A5 contagens"
$LER -A -f $PLANO/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/a5-contagens.txt
cat $W/out/a5-contagens.txt
diff <(grep -E '\|' $E7/saidas/p2-4-contagens.txt) $W/out/a5-contagens.txt > /dev/null && echo "contagens: IDÊNTICAS à P2" || diverge "contagens"
echo "== A6 migrações pelo Django (sessão somente leitura): só accounts.0006 pendente"
PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000' $P/venv/bin/python manage.py migrate --plan 2>/dev/null > $W/out/a6-migrate-plan.txt
PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000' $P/venv/bin/python manage.py migrate accounts 0006 --plan 2>/dev/null > $W/out/a6-migrate-accounts-0006-plan.txt
cat $W/out/a6-migrate-plan.txt
diff <(grep -v -E '^(AVISO|DETAIL|HINT)' $E7/saidas/p2-5-migracoes.txt | sed -n '/^Planned operations/,/^exit=/p' | grep -v '^exit=') $W/out/a6-migrate-plan.txt > /dev/null && echo "migrate --plan: IDÊNTICO à P2 (só accounts.0006)" || diverge "migrate --plan"
diff $W/out/a6-migrate-plan.txt $W/out/a6-migrate-accounts-0006-plan.txt > /dev/null && echo "migrate accounts 0006 --plan: só accounts.0006" || diverge "plano do alvo accounts 0006"
echo "== A7 processos da aplicação: $(pgrep -fa 'manage.py runserver|gunicorn|uvicorn' | grep -v pgrep | wc -l)"
echo; [ $divergencias -eq 0 ] && echo "RESULTADO A: SEM DIVERGÊNCIAS EM RELAÇÃO AO ENSAIO" || echo "RESULTADO A: $divergencias DIVERGÊNCIA(S) — PARAR"
