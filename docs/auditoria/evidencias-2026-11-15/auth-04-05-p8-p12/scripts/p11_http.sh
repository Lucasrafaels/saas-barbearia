#!/bin/bash
# P11 — testes HTTP SOMENTE com GET/HEAD/OPTIONS e sem login. Nenhum deles autentica, cria sessão ou grava no banco.
set -uo pipefail
B=http://127.0.0.1:8000; FR=http://localhost:5173
t() { # rótulo, esperado, método, url, [cabeçalhos...]
  local rot=$1 esp=$2 met=$3 url=$4; shift 4
  local r; r=$(curl -s -o /dev/null -X "$met" -w "%{http_code}|%{content_type}" "$@" "$url")
  local st=${r%%|*} ct=${r#*|}
  local ok=FALHA; [[ "$st" =~ ^($esp)$ ]] && ok="ok  "
  printf '%s %-62s %-7s %s -> %s (%s)\n' "$ok" "$rot" "$met" "${url#http://}" "$st" "${ct:-sem corpo}"
}
echo "== Backend: rotas protegidas recusam sem login (401), sem tocar no banco"
t "lista de serviços" 401 GET $B/api/v1/services/
t "dados da própria conta" 401 GET $B/api/v1/users/me/
t "agendamentos" 401 GET $B/api/v1/appointments/
t "barbearia" 401 GET $B/api/v1/barbershops/
t "barbeiros" 401 GET $B/api/v1/barbers/
echo "== Backend: rotas de escrita existem, mas só aceitam POST (aqui só GET/OPTIONS)"
t "login (GET não permitido)" 405 GET $B/api/v1/auth/login/
t "cadastro público (GET não permitido)" 405 GET $B/api/v1/auth/register/
t "cadastro público (OPTIONS, metadados)" 200 OPTIONS $B/api/v1/auth/register/
t "recuperação de senha (GET não permitido)" 405 GET $B/api/v1/auth/password/reset/
echo "== Backend: contenção do TEN-01 (só JSON; nunca HTML da API navegável)"
t "Accept: text/html" '401|406' GET $B/api/v1/services/ -H 'Accept: text/html'
t "?format=api" 404 GET "$B/api/v1/services/?format=api"
echo "== Backend: CORS do frontend (preflight OPTIONS; o navegador não envia o POST aqui)"
t "preflight do login a partir do frontend" 200 OPTIONS $B/api/v1/auth/login/ -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'
echo "   Access-Control-Allow-Origin: $(curl -s -D - -o /dev/null -X OPTIONS $B/api/v1/auth/login/ -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: POST' | tr -d '\r' | grep -i '^access-control-allow-origin' | cut -d' ' -f2)"
echo "== Backend: Django Admin (página de login, sem enviar o formulário)"
t "página de login do admin" 200 GET $B/admin/login/
echo "== Frontend (Vite)"
t "página inicial" 200 GET $FR/
t "tela de login (rota da SPA)" 200 GET $FR/login
t "tela de cadastro (rota da SPA)" 200 GET $FR/register
t "tela de recuperação (rota da SPA)" 200 GET $FR/password/reset
t "módulo principal do app" 200 GET $FR/src/main.tsx
