#!/usr/bin/env python3
"""
AUTH-05 — concorrência: dois pedidos simultâneos com o MESMO e-mail novo, contra a API de laboratório (código atual,
runserver com uma thread por pedido) sobre o PG 18.3 DESCARTÁVEL. O UniqueValidator consulta antes de gravar; entre a
consulta e o INSERT há o hash da senha (~250 ms), e o banco recusa o segundo INSERT.
Uso: python3 -I a45_concorrencia.py <estado.json> <saida.json>
"""
import json
import sys
import threading

import requests

BASE = __import__('os').environ['H_BASE'] + '/api/v1'
ESTADO = json.load(open(sys.argv[1]))
SENHA = 'Navalha-Fict-2026!'


def em_paralelo(pedidos):
    barreira = threading.Barrier(len(pedidos))
    resultados = [None] * len(pedidos)

    def rodar(i, pedido):
        metodo, caminho, corpo, token = pedido
        h = {'Accept': 'application/json'}
        if token:
            h['Authorization'] = 'Bearer ' + token
        barreira.wait()
        r = requests.request(metodo, BASE + caminho, json=corpo, headers=h, timeout=60)
        resultados[i] = r.status_code
    threads = [threading.Thread(target=rodar, args=(i, p)) for i, p in enumerate(pedidos)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return resultados


saida = []
for i in range(5):
    email = f'corrida.cadastro.{i}@exemplo.test'
    corpo = {'nome': 'Pessoa Fictícia', 'email': email, 'password': SENHA}
    saida.append({'caso': 'dois cadastros públicos simultâneos, mesmo e-mail', 'email': email,
                  'status': em_paralelo([('POST', '/auth/register/', corpo, None)] * 2)})
for i in range(5):
    email = f'corrida.criacao.{i}@exemplo.test'
    corpo = {'nome': 'Pessoa Fictícia', 'email': email, 'password': SENHA, 'tipo_perfil': 'cliente'}
    saida.append({'caso': 'admin A e admin B criam ao mesmo tempo, mesmo e-mail', 'email': email,
                  'status': em_paralelo([('POST', '/users/', corpo, ESTADO['tokens']['admin_a']),
                                         ('POST', '/users/', corpo, ESTADO['tokens']['admin_b'])])})
ids = ESTADO['ids']
for i in range(5):
    email = f'corrida.troca.{i}@exemplo.test'
    saida.append({'caso': 'cliente A1 e cliente B trocam o próprio e-mail ao mesmo tempo, para o mesmo', 'email': email,
                  'status': em_paralelo([('PATCH', f'/users/{ids["cliente_a1"]}/', {'email': email}, ESTADO['tokens']['cliente_a1']),
                                         ('PATCH', f'/users/{ids["cliente_b"]}/', {'email': email}, ESTADO['tokens']['cliente_b'])])})
for s in saida:
    print(f"{s['caso']:78} {s['status']}")
json.dump(saida, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
