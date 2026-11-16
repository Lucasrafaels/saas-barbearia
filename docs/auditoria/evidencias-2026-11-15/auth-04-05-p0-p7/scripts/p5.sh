#!/bin/bash
# P5 — restauração do backup novo no PostgreSQL 18.3 DESCARTÁVEL (127.0.0.1:55432, pt_BR.UTF-8, libc). Nada toca o banco real.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
source <(grep -E '^(ARQ)=' $W/out/variaveis.txt)
EVID=$P/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
D() { env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke "$@"; }
echo "== P5.1 ambiente descartável"
cmp -s $W/.marca-descartavel $W/pgdata/MARCA_DESCARTAVEL_AUTH0405_P07 && echo "marca do cluster descartável confere"
D -d postgres -A -c "select current_setting('data_directory') = '$W/pgdata' as diretorio_confere, inet_server_port() as porta, current_setting('server_version') as versao, current_setting('listen_addresses') as escuta"
D -d postgres -q -c "create database ensaio_restaurado template template0"
D -d postgres -A -c "select datname, datcollate, datctype, datlocprovider, datcollversion from pg_database where datname = 'ensaio_restaurado'"
echo "== P5.2 pg_restore (--no-owner --no-privileges --exit-on-error)"
set +e
pg_restore --no-owner --no-privileges --exit-on-error -h 127.0.0.1 -p 55432 -U smoke -d ensaio_restaurado "$ARQ" > $W/out/p5-pg_restore.txt 2>&1
rc=$?
set -e
echo "pg_restore exit=$rc; mensagens: $(grep -c . $W/out/p5-pg_restore.txt)"
[ $rc -eq 0 ] || { cat $W/out/p5-pg_restore.txt; echo "INTERROMPIDO: restauração com erro"; exit 1; }
echo "== P5.3 isolamento da cópia: extensões e servidores externos (esperado: só plpgsql; 0 servidores)"
D -d ensaio_restaurado -A -c "select string_agg(extname, ',') as extensoes from pg_extension" -c "select count(*) as servidores_externos from pg_foreign_server"
echo "== P5.4 contagens na cópia × banco real no momento do backup"
D -d ensaio_restaurado -A -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql 2>/dev/null | grep -E '\|' > $W/out/p5-contagens-copia.txt
diff $W/out/p4-contagens-depois.txt $W/out/p5-contagens-copia.txt && echo "contagens: IDÊNTICAS ao banco real"
echo "== P5.5 estrutura: índice do backup × dump só de esquema da cópia (sem OIDs e sem dono)"
pg_dump -h 127.0.0.1 -p 55432 -U smoke -Fc --schema-only -f $W/out/copia-esquema.dump ensaio_restaurado
norm() { pg_restore --list "$1" | grep -v '^;' | grep -v 'TABLE DATA' | grep -v 'SEQUENCE SET' | sed -E 's/^[0-9]+; [0-9]+ [0-9]+ //; s/ [^ ]+$//' | sort; }
diff <(norm "$ARQ") <(norm $W/out/copia-esquema.dump) && echo "estrutura: IDÊNTICA ao backup ($(norm "$ARQ" | wc -l) objetos)"
echo "== P5.6 as mesmas pré-verificações na cópia (devem coincidir com P2)"
D -d ensaio_restaurado -f $W/scripts/pre-verificacao-regra-exata-somente-leitura.sql > $W/out/p5-regra-exata-copia.txt 2>&1
D -d ensaio_restaurado -f $EVID/sql/01-pre-verificacao-somente-leitura.sql > $W/out/p5-pre-verificacao-copia.txt 2>&1
diff <(sed -n '/== R1/,$p' $W/out/p2-3-regra-exata.txt | grep -v -E '^exit=') <(sed -n '/== R1/,$p' $W/out/p5-regra-exata-copia.txt) && echo "regra exata: IDÊNTICA ao banco real"
diff <(sed -n '/== 2\. Migrações/,/== 5\./p' $W/out/p2-2-pre-verificacao-plano.txt) <(sed -n '/== 2\. Migrações/,/== 5\./p' $W/out/p5-pre-verificacao-copia.txt) && echo "migrações, restrições, índices e contagens da pré-verificação: IDÊNTICOS ao banco real"
