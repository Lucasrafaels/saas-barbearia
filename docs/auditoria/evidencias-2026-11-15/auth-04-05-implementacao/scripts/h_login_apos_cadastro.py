#!/usr/bin/env python3
"""AUTH-05: o fluxo da tela de cadastro (cadastra e em seguida entra com o MESMO texto digitado), contra a API de
laboratório (código atual). Uso: python3 -I a45_login_apos_cadastro.py <saida.json>"""
import json
import sys

import requests

BASE = __import__('os').environ['H_BASE'] + '/api/v1'
SENHA = 'Navalha-Fict-2026!'
saida = []
for digitado in ['pessoa.um@exemplo.test', 'Pessoa.Dois@exemplo.test', 'pessoa.tres@EXEMPLO.TEST', 'Pessoa.Quatro@Exemplo.Test']:
    c = requests.post(BASE + '/auth/register/', json={'nome': 'Pessoa Fictícia', 'email': digitado, 'password': SENHA}, timeout=60)
    l = requests.post(BASE + '/auth/login/', json={'email': digitado, 'password': SENHA}, timeout=60)
    saida.append({'digitado': digitado, 'cadastro': c.status_code, 'gravado': c.json().get('email'), 'login_com_o_mesmo_texto': l.status_code})
    print(saida[-1])
json.dump(saida, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
