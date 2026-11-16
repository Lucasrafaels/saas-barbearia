#!/bin/bash
# Limpeza: só os recursos DESCARTÁVEIS criados nesta execução, depois de reconfirmar a identidade de cada um.
set -uo pipefail
W=$1
SCRATCH=/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad
[ "$W" = "$SCRATCH/p07" ] && [ -f "$W/.marca-descartavel" ] || { echo "RECUSADO: pasta de trabalho não confere"; exit 1; }
# 1. API do ensaio (8899)
pid=$(cat $W/out/p7-runserver.pid)
if ps -o args= -p "$pid" | grep -q "runserver 127.0.0.1:8899 --noreload --settings=ensaio_fumaca_settings"; then
  kill "$pid"; sleep 1; ps -p "$pid" > /dev/null && echo "FALHA ao encerrar a API" || echo "API do ensaio encerrada (pid $pid)"
else echo "API do ensaio já não estava rodando"; fi
# 2. Cluster descartável (55432): marca, diretório de dados e porta
cmp -s $W/.marca-descartavel $W/pgdata/MARCA_DESCARTAVEL_AUTH0405_P07 || { echo "RECUSADO: marca do cluster não confere"; exit 1; }
dd=$(env -i PATH=/usr/bin:/bin psql -X -w -h 127.0.0.1 -p 55432 -U smoke -d postgres -At -c "select current_setting('data_directory') || '|' || inet_server_port()")
[ "$dd" = "$W/pgdata|55432" ] || { echo "RECUSADO: o servidor em 55432 não é o cluster desta execução ($dd)"; exit 1; }
pg_ctl -D $W/pgdata -m fast -w stop > /dev/null && echo "cluster descartável parado ($W/pgdata, porta 55432)"
# 3. Apagar só o que é descartável e desta execução
for alvo in $W/pgdata $W/codigo $W/mail $W/out/copia-esquema.dump; do
  case "$alvo" in "$W"/*) rm -rf -- "$alvo" && echo "apagado: ${alvo#$W/}";; *) echo "RECUSADO: $alvo";; esac
done
echo "porta 55432 em uso: $(ss -ltn | grep -c ':55432 ') | porta 8899 em uso: $(ss -ltn | grep -c ':8899 ')"
echo "backup preservado:"; ls -la /home/lucasrafael/backups/barberpro/ /home/lucasrafael/backups/barberpro/accounts0006_*/ | sed 's/^/  /'
