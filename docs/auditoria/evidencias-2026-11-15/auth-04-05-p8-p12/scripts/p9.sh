#!/bin/bash
# P9 — pós-verificação da accounts.0006 no BANCO REAL, somente leitura. Sem set -x; credenciais só por ambiente.
set -uo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
PLANO=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
E7=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-p0-p7
R8=$(ls -d /home/lucasrafael/backups/barberpro/accounts0006_p8_*/registro-p8)
LER="$P/venv/bin/python $PLANO/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1"
F='^\([0-9]+ (linha|linhas|row|rows)\)$'
falhas=0; falha() { echo "DIVERGÊNCIA: $1"; falhas=$((falhas+1)); }
cd $P
echo "== P9.1 identidade"
linha=$($LER -A -f $E7/scripts/identidade-somente-leitura.sql 2>/dev/null | grep -E '^barbershop_db\|'); echo "$linha"
[ "$linha" = "barbershop_db|t|18.3|::1|5432|t|on|on|pt_BR.UTF-8|pt_BR.UTF-8|c|2.43" ] && echo "identidade confirmada" || falha "identidade"
echo "== P9.2 pós-verificação do plano (02-pos-verificacao-somente-leitura.sql)"
$LER -f $PLANO/sql/02-pos-verificacao-somente-leitura.sql > $W/out/p9-pos-verificacao.txt 2>/dev/null || falha "02 falhou"
sed -n '/== 1\./,$p' $W/out/p9-pos-verificacao.txt
grep -q ' accounts | 0006_email_normalizado ' $W/out/p9-pos-verificacao.txt && echo "accounts.0006 registrada" || falha "0006 não registrada"
grep -q 'accounts_user_email_normalizado | c       | t' $W/out/p9-pos-verificacao.txt && echo "CHECK presente e validado" || falha "CHECK"
grep -q "CHECK ((((email)::text = lower((email)::text)) AND ((email)::text ~ '^\[!-~\]+\$'::text)))" $W/out/p9-pos-verificacao.txt && echo "expressão do CHECK = a aprovada" || falha "expressão do CHECK"
grep -q 'accounts_user_email_key         | u       | t' $W/out/p9-pos-verificacao.txt && echo "restrição original accounts_user_email_key preservada" || falha "accounts_user_email_key"
grep -E 'accounts_user_email_lower_unico +\| t +\| t +\| t +\| CREATE UNIQUE INDEX accounts_user_email_lower_unico ON public.accounts_user USING btree \(lower\(\(email\)::text\)\)' $W/out/p9-pos-verificacao.txt > /dev/null && echo "índice único em lower(email) presente, válido e pronto" || falha "índice lower"
grep -A3 '== 4\.' $W/out/p9-pos-verificacao.txt | grep -q -E '^ +8 \| +0$' && echo "8 contas, 0 fora da regra do CHECK" || falha "contas/regra"
echo "== P9.3 regra exata da migração (todas as contas na forma canônica)"
$LER -f $E7/scripts/pre-verificacao-regra-exata-somente-leitura.sql > $W/out/p9-regra-exata.txt 2>/dev/null || falha "regra exata falhou"
sed -n '/== R1/,/== R2/p' $W/out/p9-regra-exata.txt | head -5
grep -A3 '== R1' $W/out/p9-regra-exata.txt | grep -q -E '^ +8 \| +8 \| +0 \| +0 \| +0$' && echo "8 contas, 8 canônicas, 0 a normalizar, 0 fora, 0 colisões" || falha "regra exata"
echo "== P9.4 contagens (esperado: iguais às de antes da P8, exceto django_migrations +1 pelo registro da 0006)"
$LER -A -f $PLANO/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/p9-contagens.txt; cat $W/out/p9-contagens.txt
diff <(grep -v django_migrations $R8/a5-contagens.txt) <(grep -v django_migrations $W/out/p9-contagens.txt) > /dev/null && echo "todas as tabelas iguais às de antes da P8, fora django_migrations" || falha "contagens"
echo "django_migrations: antes $(grep '^django_migrations' $R8/a5-contagens.txt | cut -d'|' -f2), agora $(grep '^django_migrations' $W/out/p9-contagens.txt | cut -d'|' -f2)"
[ "$(grep '^django_migrations' $W/out/p9-contagens.txt | cut -d'|' -f2)" = 54 ] || falha "django_migrations esperado 54"
echo "== P9.5 migrações pelo Django (sessão somente leitura)"
{ PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000' $P/venv/bin/python manage.py showmigrations accounts 2>/dev/null; echo '--- migrate --plan'; PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000' $P/venv/bin/python manage.py migrate --plan 2>/dev/null; echo '--- migrate --check'; PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000' $P/venv/bin/python manage.py migrate --check 2>/dev/null; echo "migrate --check exit=$?"; } > $W/out/p9-migracoes.txt
cat $W/out/p9-migracoes.txt
grep -q '\[X\] 0006_email_normalizado' $W/out/p9-migracoes.txt && grep -q 'No planned migration operations' $W/out/p9-migracoes.txt && grep -q 'migrate --check exit=0' $W/out/p9-migracoes.txt && echo "nenhuma migração pendente" || falha "migrações pendentes"
echo "== P9.6 contadores de escrita do PostgreSQL (linha de base para P10/P11)"
$LER -A -f $W/estatisticas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/estatisticas-s0-depois-p9.txt; wc -l < $W/out/estatisticas-s0-depois-p9.txt | sed 's/^/tabelas: /'
echo; [ $falhas -eq 0 ] && echo "RESULTADO P9: APROVADA" || echo "RESULTADO P9: $falhas DIVERGÊNCIA(S) — NÃO SEGUIR PARA A P10"
