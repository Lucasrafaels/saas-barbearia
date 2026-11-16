#!/usr/bin/env python3
"""
Plano da accounts.0006 (seção 32), passos P7 e P11: testes de fumaça pela API HTTP.
NÃO FOI EXECUTADO na etapa de planejamento. Ler inteiro antes de usar.

Modos:
  completo    SÓ na CÓPIA DESCARTÁVEL (P7). Cria dados fictícios: conta pública com maiúsculas, login com o mesmo
              texto, onboarding de uma barbearia fictícia, serviço, barbeiro, cliente, agendamento pelo dono, login do
              cliente com outra caixa e agendamento pelo cliente, recuperação de senha (o backend de e-mail do ensaio
              é locmem, nada sai), variação de caixa recusada (400), e-mail não ASCII recusado (400).
  sem-escrita No BANCO REAL (P11), só pedidos que não gravam nada: API no ar, login errado de conta fictícia
              inexistente (401), cadastro com e-mail não ASCII (400), cadastro com a variação de caixa do e-mail
              informado em FUMACA_EMAIL_EXISTENTE (400, sem criar conta) e recuperação de e-mail fictício inexistente
              (204: a aplicação faz o envio fictício de sempre para DEFAULT_FROM_EMAIL).

Nunca imprime senhas nem tokens. O e-mail existente (modo sem-escrita) vem da variável de ambiente
FUMACA_EMAIL_EXISTENTE e não é impresso. Para executar, use o python3 do sistema, que tem o `requests`.

Uso: python3 -I fumaca.py <completo|sem-escrita> <URL base, por exemplo http://127.0.0.1:8899>
Sai com código 1 se qualquer verificação falhar.
"""
import os
import secrets
import sys
from datetime import date, timedelta

import requests

MODO, BASE = sys.argv[1], sys.argv[2].rstrip('/') + '/api/v1'
assert MODO in ('completo', 'sem-escrita'), MODO
SENHA = 'Fumaca-' + secrets.token_urlsafe(10)
SUFIXO = secrets.token_hex(4)
falhas = []


def conferir(rotulo, resposta, esperado):
    ok = resposta.status_code == esperado
    print(f"{'ok  ' if ok else 'FALHA'} {rotulo}: {resposta.status_code} (esperado {esperado})")
    if not ok:
        falhas.append(rotulo)
    return resposta


def post(caminho, corpo, token=None):
    h = {'Authorization': f'Bearer {token}'} if token else {}
    return requests.post(BASE + caminho, json=corpo, headers=h, timeout=30)


def entrar(email):
    r = post('/auth/login/', {'email': email, 'password': SENHA})
    return r, (r.json().get('access') if r.status_code == 200 else None)


if MODO == 'sem-escrita':
    conferir('API no ar (lista de serviços sem login)', requests.get(BASE + '/services/', timeout=30), 401)
    conferir('login errado de conta fictícia inexistente', post('/auth/login/', {'email': f'fumaca.{SUFIXO}@exemplo.test',
                                                                                'password': 'Errada-123!'}), 401)
    conferir('cadastro com e-mail não ASCII', post('/auth/register/', {'nome': 'Fumaça', 'email': f'fumaça.{SUFIXO}@exemplo.test',
                                                                       'password': SENHA}), 400)
    existente = os.environ.get('FUMACA_EMAIL_EXISTENTE')
    if existente:
        conferir('cadastro com a variação de caixa de um e-mail existente', post('/auth/register/', {
            'nome': 'Fumaça', 'email': existente.strip().upper(), 'password': SENHA}), 400)
    conferir('recuperação de e-mail fictício inexistente', post('/auth/password/reset/', {'email': f'fumaca.{SUFIXO}@exemplo.test'}), 204)
else:
    dono_digitado = f'Dono.Fumaca.{SUFIXO}@EXEMPLO.TEST'
    conferir('cadastro público com maiúsculas', post('/auth/register/', {'nome': 'Dono Fumaça', 'email': dono_digitado, 'password': SENHA}), 201)
    _, dono = entrar(dono_digitado)
    conferir('login logo após o cadastro, com o mesmo texto', entrar(dono_digitado)[0], 200)
    conferir('variação de caixa recusada', post('/auth/register/', {'nome': 'X', 'email': dono_digitado.lower(), 'password': SENHA}), 400)
    conferir('e-mail não ASCII recusado', post('/auth/register/', {'nome': 'X', 'email': f'fumaça.{SUFIXO}@exemplo.test', 'password': SENHA}), 400)
    loja = conferir('onboarding da barbearia fictícia', post('/barbershops/', {
        'nome': f'Barbearia Fumaça {SUFIXO}', 'endereco': 'Rua Exemplo, 1', 'telefone': '11900000000',
        'email': f'contato.{SUFIXO}@exemplo.test', 'horario_abertura': '08:00', 'horario_fechamento': '18:00'}, dono), 201)
    servico = conferir('serviço', post('/services/', {'nome': 'Corte Fumaça', 'preco': '30.00', 'duracao': 30}, dono), 201)
    conferir('barbeiro criado pelo admin', post('/users/', {'email': f'Barbeiro.{SUFIXO}@Exemplo.Test', 'nome': 'Barbeiro Fumaça',
                                                            'password': SENHA, 'tipo_perfil': 'barbeiro', 'especialidade': 'Corte'}, dono), 201)
    cliente = conferir('cliente criado pelo admin', post('/users/', {'email': f' Cliente.{SUFIXO}@EXEMPLO.test ', 'nome': 'Cliente Fumaça',
                                                                     'password': SENHA, 'tipo_perfil': 'cliente'}, dono), 201)
    barbeiros = requests.get(BASE + '/barbers/', headers={'Authorization': f'Bearer {dono}'}, timeout=30).json().get('results', [])
    barbeiro_id = next((b['id'] for b in barbeiros if b.get('email') == f'barbeiro.{SUFIXO}@exemplo.test'), None)
    dia = date.today() + timedelta(days=3)
    if servico.status_code == 201 and cliente.status_code == 201 and barbeiro_id:
        conferir('agendamento pelo dono', post('/appointments/', {'cliente': cliente.json()['id'], 'barbeiro': barbeiro_id,
                                                                  'servico': servico.json()['id'], 'data_hora': f'{dia}T10:00:00'}, dono), 201)
        _, token_cliente = entrar(f'CLIENTE.{SUFIXO}@exemplo.test')
        conferir('login do cliente com outra caixa', entrar(f'CLIENTE.{SUFIXO}@exemplo.test')[0], 200)
        conferir('agendamento pelo próprio cliente', post('/appointments/', {'cliente': cliente.json()['id'], 'barbeiro': barbeiro_id,
                                                                             'servico': servico.json()['id'], 'data_hora': f'{dia}T11:00:00'},
                                                          token_cliente), 201)
    else:
        falhas.append('preparação do agendamento')
    conferir('recuperação de senha com outra caixa', post('/auth/password/reset/', {'email': dono_digitado.swapcase()}), 204)
    del loja

print('RESULTADO:', 'OK' if not falhas else f'{len(falhas)} falha(s): {falhas}')
sys.exit(1 if falhas else 0)
