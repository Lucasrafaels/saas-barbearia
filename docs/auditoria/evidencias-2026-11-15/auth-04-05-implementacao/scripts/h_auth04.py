#!/usr/bin/env python3
"""
AUTH-04 — demonstração com contas fictícias, contra a API de laboratório (código ATUAL, sem alteração, DEBUG=False)
sobre o PG 18.3 DESCARTÁVEL. Segue cada token de recuperação: para qual conta foi gerado (uid decodificado), para
qual endereço foi enviado, e o que acontece ao usá-lo.

Uso: python3 -I a45_auth04.py <estado.json> <pasta EMAIL_FILE_PATH> <saida.json>
O token de recuperação é usado só aqui e nunca é gravado na saída.
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

import requests

BASE = __import__('os').environ['H_BASE'] + '/api/v1'
ESTADO, MAIL, SAIDA = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
CREDS, IDS, TOKENS = ESTADO['creds'], ESTADO['ids'], ESTADO['tokens']
NOVA = 'Nova-Senha-Ficticia-2026!'
FORTE = 'Navalha-Fict-2026!'
passos = []


def contas_por_id():
    r = subprocess.run(['psql', '-X', '-w', '-A', '-t', '-F', '\t', '-h', '127.0.0.1', '-p', '55432', '-U', 'smoke', '-d', __import__('os').environ['H_DB'],
                        '-c', 'select id, email, nome, coalesce(barbershop_id::text, \'null\'), is_active from accounts_user order by id'],
                       capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'}, check=True)
    return {int(l.split('\t')[0]): dict(zip(['id', 'email', 'nome', 'barbershop_id', 'is_active'], l.split('\t')))
            for l in r.stdout.splitlines() if l}


def pedir(passo, metodo, caminho, corpo, papel=None):
    h = {'Accept': 'application/json'}
    if papel:
        h['Authorization'] = 'Bearer ' + TOKENS[papel]
    antes = set(os.listdir(MAIL))
    r = requests.request(metodo, BASE + caminho, json=corpo, headers=h, timeout=60)
    time.sleep(0.2)
    mensagens = []
    for nome in sorted(set(os.listdir(MAIL)) - antes):
        texto = open(os.path.join(MAIL, nome), encoding='utf-8').read()
        uid = re.search(r'^uid: (\S+)$', texto, re.M).group(1)
        token = re.search(r'^token: (\S+)$', texto, re.M).group(1)
        conta = int(base64.urlsafe_b64decode(uid + '=' * (-len(uid) % 4)).decode())
        mensagens.append({'para': re.findall(r'^To: (.*)$', texto, re.M), 'uid_da_conta': conta, '_uid': uid, '_token': token})
    enviado = {k: ('<senha omitida>' if 'password' in k else ('<token omitido>' if k in ('token',) else v)) for k, v in corpo.items()}
    reg = {'passo': passo, 'pedido': f'{metodo} /api/v1{caminho}', 'papel': papel or 'anônimo', 'corpo_enviado': enviado,
           'status': r.status_code, 'resposta': r.text if 'access' not in r.text else '{"access": "<token removido>"}',
           'emails_de_recuperacao': [{k: v for k, v in m.items() if not k.startswith('_')} for m in mensagens]}
    passos.append(reg)
    print(f"{passo:58} {r.status_code}  {reg['resposta'][:90]}  {reg['emails_de_recuperacao']}")
    return r, mensagens


vitima = CREDS['cliente_b']
# A1 — controle: sem variação, a recuperação da vítima vai para a própria vítima.
_, m = pedir('A1 controle: recuperação da vítima, sem variação', 'POST', '/auth/password/reset/', {'email': vitima['email']})
# A2 — um anônimo cadastra a variação de caixa, com um nome que vem antes de "Clara" na ordem alfabética.
r, _ = pedir('A2 terceiro cadastra "Cliente.B@beta.test" (nome "Aaron")', 'POST', '/auth/register/',
             {'nome': 'Aaron Variante', 'email': 'Cliente.B@beta.test', 'password': FORTE})
id_variante = r.json().get('id')
# A3/A4 — a vítima pede a recuperação, em minúsculas e em maiúsculas.
_, m3 = pedir('A3 vítima pede recuperação com "cliente.b@beta.test"', 'POST', '/auth/password/reset/', {'email': vitima['email']})
m3 = m3 or [{'_uid': '', '_token': ''}]
pedir('A4 vítima pede recuperação com "CLIENTE.B@BETA.TEST"', 'POST', '/auth/password/reset/', {'email': 'CLIENTE.B@BETA.TEST'})
# A5 — a vítima usa o token que recebeu.
pedir('A5 vítima confirma com o uid e o token recebidos em A3', 'POST', '/auth/password/reset/confirm/',
      {'uid': m3[0]['_uid'], 'token': m3[0]['_token'], 'new_password': NOVA})
# A6 — efeito: qual conta teve a senha trocada.
pedir('A6a login "cliente.b@beta.test" + senha NOVA', 'POST', '/auth/login/', {'email': vitima['email'], 'password': NOVA})
pedir('A6b login "cliente.b@beta.test" + senha ANTIGA', 'POST', '/auth/login/', {'email': vitima['email'], 'password': vitima['password']})
pedir('A6c login "Cliente.B@beta.test" + senha NOVA', 'POST', '/auth/login/', {'email': 'Cliente.B@beta.test', 'password': NOVA})
# A7 — a ordem importa: variação com nome que vem DEPOIS do da vítima ("Celia" < "Zuleica").
pedir('A7a terceiro cadastra "Cliente.A2@alfa.test" (nome "Zuleica")', 'POST', '/auth/register/',
      {'nome': 'Zuleica Variante', 'email': 'Cliente.A2@alfa.test', 'password': FORTE})
pedir('A7b recuperação de "cliente.a2@alfa.test"', 'POST', '/auth/password/reset/', {'email': CREDS['cliente_a2']['email']})
# A8 — a variação criada por um admin dentro da própria barbearia (A) desvia a recuperação de alguém de B para A.
r, _ = pedir('A8a admin A cria cliente "ADMIN.B@beta.test" (nome "Abel") na barbearia A', 'POST', '/users/',
             {'nome': 'Abel Variante', 'email': 'ADMIN.B@beta.test', 'password': FORTE, 'tipo_perfil': 'cliente'}, papel='admin_a')
id_abel = r.json().get('id')
pedir('A8b recuperação de "admin.b@beta.test" (admin de B)', 'POST', '/auth/password/reset/', {'email': CREDS['admin_b']['email']})
# A9 — conta inativa não é escolhida: o admin A desativa a variação e a recuperação volta para a vítima.
if id_abel is not None:  # no código corrigido a variação não chega a existir
    pedir('A9a admin A desativa o cliente "Abel"', 'DELETE', f'/users/{id_abel}/', {}, papel='admin_a')
    pedir('A9b recuperação de "admin.b@beta.test" de novo', 'POST', '/auth/password/reset/', {'email': CREDS['admin_b']['email']})

contas = contas_por_id()
# Invariante: todo token foi enviado ao e-mail gravado na PRÓPRIA conta para a qual foi gerado.
verificacao = []
for p in passos:
    for e in p['emails_de_recuperacao']:
        conta = contas.get(e['uid_da_conta'])
        verificacao.append({'passo': p['passo'], 'para': e['para'], 'conta': conta,
                            'destinatario_e_o_email_da_propria_conta': conta is not None and e['para'] == [conta['email']]})
saida = {'contas_no_fim': contas, 'ids': {'vitima_cliente_b': IDS['cliente_b'], 'variante_aaron': id_variante,
                                          'vitima_cliente_a2': IDS['cliente_a2'], 'vitima_admin_b': IDS['admin_b'], 'variante_abel': id_abel},
         'passos': passos, 'invariante_token_x_destinatario': verificacao}
json.dump(saida, open(SAIDA, 'w'), ensure_ascii=False, indent=1)
print('\ninvariante (token sempre para o e-mail da própria conta):', all(v['destinatario_e_o_email_da_propria_conta'] for v in verificacao),
      f'({len(verificacao)} mensagens)')
