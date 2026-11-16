#!/usr/bin/env python3
"""
Mitigação D do TEN-03 — sondagem HTTP de antes e depois, com as taxas REAIS, contra uma API de laboratório sobre
um banco DESCARTÁVEL (PG 18.3, 127.0.0.1:55432). Cada pedido fica entre dois marcadores no log do PostgreSQL
(log_statement = 'all' só nesse banco), para depois conferir se a unicidade do e-mail foi consultada.

Uso: python3 -I d_probe.py <base_url> <banco> <estado.json> <saida.json>
Dados fictícios (domínios .test); 203.0.113.0/24 e 198.51.100.0/24 são faixas reservadas para documentação.
"""
import json
import subprocess
import sys
import time

import requests

BASE, BANCO, ESTADO, SAIDA = sys.argv[1] + '/api/v1', sys.argv[2], json.load(open(sys.argv[3])), sys.argv[4]
CREDS, IDS, TOKENS = ESTADO['creds'], ESTADO['ids'], ESTADO['tokens']
FRACA = '12345678'
FORTE = 'Navalha-Fict-2026!'
EXISTENTE = CREDS['cliente_b']['email']
seq = {'n': 0}
registros = []


def psql(sql):
    subprocess.run(['psql', '-X', '-w', '-q', '-h', '127.0.0.1', '-p', '55432', '-U', 'smoke', '-d', BANCO, '-c', sql],
                   check=True, capture_output=True, env={'PATH': '/usr/bin:/bin'})


def livre():
    seq['n'] += 1
    return f'livre.{seq["n"]}@exemplo.test'


def pedir(etapa, metodo, caminho, corpo, papel=None, cabecalhos=None, email=None):
    h = {'Accept': 'application/json', **(cabecalhos or {})}
    if papel:
        h['Authorization'] = 'Bearer ' + TOKENS[papel]
    rid = f'{etapa}-{len(registros):03d}'
    psql(f"select 'DMARK {rid} inicio'")
    r = requests.request(metodo, BASE + caminho, json=corpo, headers=h, timeout=60)
    psql(f"select 'DMARK {rid} fim'")
    enviado = {k: ('<senha omitida>' if 'password' in k else v) for k, v in (corpo or {}).items()}
    registros.append({'id': rid, 'etapa': etapa, 'pedido': f'{metodo} /api/v1{caminho}', 'papel': papel or 'anônimo',
                      'cabecalhos_extras': cabecalhos or {}, 'email_sondado': email, 'corpo_enviado': enviado,
                      'status': r.status_code, 'retry_after': r.headers.get('Retry-After'),
                      'content_type': r.headers.get('Content-Type'),
                      'resposta': r.text if r.status_code != 200 or 'access' not in r.text else '{"access": "<token removido>"}'})
    return r


def alternar(n):
    return [EXISTENTE if i % 2 else livre() for i in range(n)]


# 1. Cadastro público (anônimo): 25 tentativas sem efeito colateral (senha que cai nos validadores).
for email in alternar(25):
    pedir('cadastro', 'POST', '/auth/register/', {'nome': 'Pessoa Fictícia', 'email': email, 'password': FRACA}, email=email)
# 2. Limitação conhecida: o mesmo anônimo, com X-Forwarded-For forjado, ganha uma cota nova a cada valor.
for i in range(1, 6):
    pedir('cadastro-xff', 'POST', '/auth/register/', {'nome': 'Pessoa Fictícia', 'email': EXISTENTE, 'password': FRACA},
          cabecalhos={'X-Forwarded-For': f'203.0.113.{i}'}, email=EXISTENTE)
# 3. Criação de usuário pelo admin A: 40 tentativas sem efeito colateral.
for email in alternar(40):
    pedir('criacao', 'POST', '/users/', {'nome': 'Cliente Fictício', 'email': email, 'password': FRACA, 'tipo_perfil': 'cliente'},
          papel='admin_a', email=email)
# 4. Outro admin (de B) não foi afetado: criação legítima.
pedir('criacao-outro-admin', 'POST', '/users/', {'nome': 'Cliente Novo B', 'email': livre(), 'password': FORTE, 'tipo_perfil': 'cliente'},
      papel='admin_b')
# 5. Troca do próprio e-mail pelo cliente A1: 15 tentativas sem efeito colateral (nome vazio).
a1 = IDS['cliente_a1']
for email in alternar(15):
    pedir('troca', 'PATCH', f'/users/{a1}/', {'nome': '', 'email': email}, papel='cliente_a1', email=email)
# 6. Edições que não trocam o e-mail continuam funcionando para quem esgotou a cota.
pedir('edicao-sem-troca', 'PATCH', f'/users/{a1}/', {'nome': 'Carlos Cliente A1', 'email': CREDS['cliente_a1']['email']}, papel='cliente_a1')
pedir('edicao-sem-troca', 'PATCH', f'/users/{a1}/', {'nome': 'Carlos Cliente A1'}, papel='cliente_a1')
# 7. A vítima (cliente B), cujo e-mail foi sondado: troca o próprio e-mail, entra e pede recuperação.
novo_b = livre()
pedir('vitima', 'PATCH', f'/users/{IDS["cliente_b"]}/', {'email': novo_b}, papel='cliente_b')
pedir('vitima', 'POST', '/auth/login/', {'email': novo_b, 'password': CREDS['cliente_b']['password']})
pedir('vitima', 'POST', '/auth/password/reset/', {'email': novo_b})
# 8. Login: o limite (5 por minuto, por origem) continua o mesmo. Já houve 1 login acima.
for _ in range(5):
    pedir('login', 'POST', '/auth/login/', {'email': CREDS['admin_a']['email'], 'password': 'Senha-Errada-123!'})
# 9. Recuperação: a mesma resposta para existente e livre. Já houve 1 acima (limite 5/hora).
pedir('recuperacao', 'POST', '/auth/password/reset/', {'email': CREDS['cliente_a2']['email']})
pedir('recuperacao', 'POST', '/auth/password/reset/', {'email': livre()})

time.sleep(1)
json.dump(registros, open(SAIDA, 'w'), ensure_ascii=False, indent=1)
for r in registros:
    print(f"{r['id']:26} {r['status']} RA={r['retry_after']!s:6} {r['resposta'][:110]}")
