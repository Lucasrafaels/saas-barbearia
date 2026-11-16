#!/usr/bin/env python3
"""
AUTH-05 — matriz do tratamento do e-mail, fluxo × variação, contra a API de laboratório (código ATUAL, sem alteração,
DEBUG=False) sobre o PG 18.3 DESCARTÁVEL. Para cada pedido: status, resposta, o valor GRAVADO no banco e se surgiu
conta equivalente (mesmo e-mail sem diferenciar caixa). O estado é restaurado entre os casos.

Uso: python3 -I a45_auth05_matriz.py <estado.json> <pasta EMAIL_FILE_PATH> <saida.json>
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

import requests

BASE = 'http://127.0.0.1:8801/api/v1'
ESTADO, MAIL, SAIDA = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
CREDS, IDS, TOKENS = ESTADO['creds'], ESTADO['ids'], ESTADO['tokens']
FORTE = 'Navalha-Fict-2026!'
EXISTENTE = CREDS['cliente_a1']['email']          # cliente.a1@alfa.test
ALVO_PATCH = IDS['cliente_a2']                     # quem troca o próprio e-mail
EMAIL_ORIGINAL_ALVO = CREDS['cliente_a2']['email']


def psql(sql):
    r = subprocess.run(['psql', '-X', '-w', '-A', '-t', '-F', '\t', '-h', '127.0.0.1', '-p', '55432', '-U', 'smoke', '-d', 'a45_db',
                        '-c', sql], capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'}, check=True)
    return r.stdout.strip()


def lit(s):
    return "'" + s.replace("'", "''") + "'"


MAX_ID = int(psql('select max(id) from accounts_user'))


def restaurar():
    psql(f'delete from token_blacklist_outstandingtoken where user_id > {MAX_ID}; delete from barbershops_barber where user_id > {MAX_ID};'
         f' delete from accounts_user where id > {MAX_ID};'
         f' update accounts_user set email = {lit(EMAIL_ORIGINAL_ALVO)} where id = {ALVO_PATCH}')


def equivalentes(valor):
    out = psql(f'select id, email from accounts_user where lower(email) = lower(btrim({lit(valor)})) order by id')
    return [l.replace('\t', ' ') for l in out.splitlines()]


VARIACOES = [
    ('novo, minúsculas', 'novo.{n}@exemplo.test'),
    ('novo, maiúsculas na parte local', 'Novo.{n}@exemplo.test'),
    ('novo, maiúsculas no domínio', 'novo.{n}@EXEMPLO.TEST'),
    ('novo, tudo maiúsculo', 'NOVO.{n}@EXEMPLO.TEST'),
    ('novo, com espaços', '  novo.{n}@exemplo.test  '),
    ('existente, exato', EXISTENTE),
    ('existente, maiúsculas na parte local', 'Cliente.A1@alfa.test'),
    ('existente, maiúsculas no domínio', 'cliente.a1@ALFA.TEST'),
    ('existente, tudo maiúsculo', 'CLIENTE.A1@ALFA.TEST'),
    ('existente, com espaços', f'  {EXISTENTE}  '),
]
FLUXOS = [
    ('cadastro público', None, 'POST', '/auth/register/', lambda e: {'nome': 'Pessoa Fictícia', 'email': e, 'password': FORTE}),
    ('criação pelo admin', 'admin_a', 'POST', '/users/', lambda e: {'nome': 'Pessoa Fictícia', 'email': e, 'password': FORTE, 'tipo_perfil': 'cliente'}),
    ('troca do próprio e-mail', 'cliente_a2', 'PATCH', f'/users/{ALVO_PATCH}/', lambda e: {'email': e}),
]
linhas = []
n = 0
for fluxo, papel, metodo, caminho, corpo in FLUXOS:
    for rotulo, molde in VARIACOES:
        n += 1
        restaurar()
        valor = molde.format(n=n)
        h = {'Accept': 'application/json'}
        if papel:
            h['Authorization'] = 'Bearer ' + TOKENS[papel]
        r = requests.request(metodo, BASE + caminho, json=corpo(valor), headers=h, timeout=60)
        gravado = psql(f'select email from accounts_user where id = {ALVO_PATCH}') if metodo == 'PATCH' else (
            (r.json().get('email') if r.status_code == 201 else None))
        eq = equivalentes(valor)
        linhas.append({'fluxo': fluxo, 'variacao': rotulo, 'enviado': valor, 'status': r.status_code,
                       'resposta': r.text if r.status_code != 500 else 'HTML "Server Error (500)"',
                       'gravado': gravado, 'contas_equivalentes_depois': eq, 'duplicata': len(eq) > 1})
        print(f'{fluxo:24} {rotulo:38} {r.status_code}  gravado={gravado!s:28} equivalentes={len(eq)}')
restaurar()

# Login com a senha CORRETA do cliente A1, variando o e-mail.
for rotulo, valor in [('exato', EXISTENTE), ('maiúsculas na parte local', 'Cliente.A1@alfa.test'),
                      ('maiúsculas no domínio', 'cliente.a1@ALFA.TEST'), ('tudo maiúsculo', 'CLIENTE.A1@ALFA.TEST'),
                      ('com espaços', f'  {EXISTENTE}  ')]:
    r = requests.post(BASE + '/auth/login/', json={'email': valor, 'password': CREDS['cliente_a1']['password']}, timeout=60)
    linhas.append({'fluxo': 'login (senha correta)', 'variacao': rotulo, 'enviado': valor, 'status': r.status_code,
                   'resposta': r.text if r.status_code != 200 else '{"access": "<token removido>"}'})
    print(f'{"login (senha correta)":24} {rotulo:38} {r.status_code}')

# Recuperação de senha, variando o e-mail de uma conta sem variações gravadas: qual conta recebe.
for rotulo, valor in [('exato', EXISTENTE), ('maiúsculas na parte local', 'Cliente.A1@alfa.test'),
                      ('tudo maiúsculo', 'CLIENTE.A1@ALFA.TEST'), ('com espaços', f'  {EXISTENTE}  ')]:
    antes = set(os.listdir(MAIL))
    r = requests.post(BASE + '/auth/password/reset/', json={'email': valor}, timeout=60)
    time.sleep(0.2)
    contas = []
    for f in sorted(set(os.listdir(MAIL)) - antes):
        t = open(os.path.join(MAIL, f), encoding='utf-8').read()
        uid = re.search(r'^uid: (\S+)$', t, re.M).group(1)
        contas.append({'para': re.findall(r'^To: (.*)$', t, re.M),
                       'uid_da_conta': int(base64.urlsafe_b64decode(uid + '=' * (-len(uid) % 4)).decode())})
    linhas.append({'fluxo': 'recuperação de senha', 'variacao': rotulo, 'enviado': valor, 'status': r.status_code, 'emails': contas})
    print(f'{"recuperação de senha":24} {rotulo:38} {r.status_code}  {contas}')
json.dump(linhas, open(SAIDA, 'w'), ensure_ascii=False, indent=1)
