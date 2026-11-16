#!/bin/bash
# P0 — preparação. Não toca em banco nenhum. Não altera o repositório original.
set -euo pipefail
umask 077
P=/home/lucasrafael/arquivos_faculdade/saas_barbearia
W=$1
TS=$(date +%Y%m%d_%H%M%S)
BD=/home/lucasrafael/backups/barberpro/accounts0006_$TS
echo "TS=$TS" > $W/out/variaveis.txt
echo "BD=$BD" >> $W/out/variaveis.txt
# Estado do repositório original (para provar, no fim, que nada mudou).
cd $P
git status --short > $W/out/git-status-antes.txt
git ls-files -m -o --exclude-standard -c | grep -v -E '^(venv|venv312|frontend/node_modules)/' | sort -u | xargs sha256sum > $W/out/hashes-repo-antes.txt 2>/dev/null || true
# Diretório exclusivo do backup, privado.
test ! -e "$BD"
mkdir -m 700 "$BD"
echo "diretório do backup criado: $(stat -c '%a %U %n' "$BD")"
# Cópia isolada só do backend necessário para rodar a aplicação e os testes (sem .env, venv, .git, docs, mídia, bancos).
mkdir -p $W/codigo
cp -a manage.py requirements.txt config accounts barbershops services appointments $W/codigo/
find $W/codigo -name '__pycache__' -type d -prune -exec rm -rf {} +
test ! -e $W/codigo/.env
( cd $W/codigo && find . -type f | sort | xargs sha256sum ) > $W/out/hashes-copia.txt
( cd $P && awk '{print $2}' $W/out/hashes-copia.txt | xargs sha256sum ) > $W/out/hashes-originais-dos-copiados.txt
diff -q $W/out/hashes-copia.txt $W/out/hashes-originais-dos-copiados.txt && echo "cópia idêntica ao original: $(wc -l < $W/out/hashes-copia.txt) arquivos"
# Retrato do código para eventual retorno (plano P0/R3), sem segredos nem dependências.
test ! -e "$BD/codigo_$TS.tar.gz"
tar --exclude=./venv --exclude=./venv312 --exclude=./frontend/node_modules --exclude=./frontend/dist --exclude=./.git \
    --exclude=./.env --exclude=./media --exclude='*.sqlite3' --exclude=./test.db --exclude=./docs --exclude=./outputs \
    --exclude=./work --exclude=./references --exclude='*/__pycache__' --exclude=./__pycache__ --exclude=./.pytest_cache \
    -czf "$BD/codigo_$TS.tar.gz" .
tar -tzf "$BD/codigo_$TS.tar.gz" | grep -c -E '(^|/)\.env$' | sed 's/^/arquivos .env no retrato (esperado 0): /'
( cd "$BD" && sha256sum "codigo_$TS.tar.gz" > "codigo_$TS.tar.gz.sha256" )
stat -c '%a %s %n' "$BD"/codigo_$TS.tar.gz "$BD"/codigo_$TS.tar.gz.sha256
