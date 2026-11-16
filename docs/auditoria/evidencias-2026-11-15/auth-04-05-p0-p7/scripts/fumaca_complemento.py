#!/usr/bin/env python3
"""
P7 — complemento do fumaca.py (modo completo), SÓ NA CÓPIA DESCARTÁVEL: edição de e-mail, recuperação de senha seguida
até a troca (e-mail capturado em arquivo local), isolamento entre duas barbearias fictícias e a ausência de contas reais
na visão de um admin fictício. Dados fictícios (exemplo.test). Não imprime e-mails reais, senhas nem tokens.
Uso: python3 -I fumaca_complemento.py <URL base> <pasta de e-mails capturados>
"""
import base64
import os
import re
import secrets
import sys
import time

import requests

BASE, MAIL = sys.argv[1].rstrip('/') + '/api/v1', sys.argv[2]
S = secrets.token_hex(4)
SENHA, NOVA = 'Fumaca-' + secrets.token_urlsafe(10), 'Fumaca-Nova-' + secrets.token_urlsafe(10)
falhas = []


def conferir(rotulo, condicao, detalhe=''):
    print(f"{'ok  ' if condicao else 'FALHA'} {rotulo}{(': ' + detalhe) if detalhe else ''}")
    if not condicao:
        falhas.append(rotulo)


def req(metodo, caminho, corpo=None, token=None):
    h = {'Authorization': f'Bearer {token}'} if token else {}
    return requests.request(metodo, BASE + caminho, json=corpo, headers=h, timeout=30)


def token(email, senha=SENHA):
    r = req('POST', '/auth/login/', {'email': email, 'password': senha})
    return r.status_code, (r.json().get('access') if r.status_code == 200 else None)


def dono(rotulo):
    email = f'Dono.{rotulo}.{S}@EXEMPLO.TEST'
    conferir(f'cadastro público do dono {rotulo}', req('POST', '/auth/register/', {'nome': f'Dono {rotulo}', 'email': email, 'password': SENHA}).status_code == 201)
    st, tk = token(email)
    conferir(f'login do dono {rotulo}', st == 200, str(st))
    r = req('POST', '/barbershops/', {'nome': f'Barbearia {rotulo} {S}', 'endereco': 'Rua Exemplo, 9', 'telefone': '11900000000',
                                      'email': f'contato.{rotulo.lower()}.{S}@exemplo.test', 'horario_abertura': '08:00',
                                      'horario_fechamento': '18:00'}, tk)
    conferir(f'criação da barbearia {rotulo}', r.status_code == 201, str(r.status_code))
    return tk, r.json().get('id')


# Duas barbearias fictícias (A e B), um cliente em cada.
tk_a, loja_a = dono('A')
tk_b, loja_b = dono('B')
cli_a = req('POST', '/users/', {'email': f' Cliente.A.{S}@Exemplo.Test ', 'nome': 'Cliente A', 'password': SENHA, 'tipo_perfil': 'cliente'}, tk_a)
cli_b = req('POST', '/users/', {'email': f'cliente.b.{S}@exemplo.test', 'nome': 'Cliente B', 'password': SENHA, 'tipo_perfil': 'cliente'}, tk_b)
conferir('cadastro administrativo de cliente (A, com maiúsculas e espaços)', cli_a.status_code == 201 and cli_a.json()['email'] == f'cliente.a.{S}@exemplo.test')
conferir('cadastro administrativo de cliente (B)', cli_b.status_code == 201)
id_a, id_b = cli_a.json().get('id'), cli_b.json().get('id')

# Isolamento entre barbearias (e nenhuma conta real visível para o admin fictício).
lista = req('GET', '/users/', token=tk_a).json()
conferir('admin A só lista contas da barbearia A', lista.get('count') == 2 and all(u['barbershop'] == loja_a for u in lista.get('results', [])),
         f"count={lista.get('count')}")
conferir('admin A não lê o cliente de B (404)', req('GET', f'/users/{id_b}/', token=tk_a).status_code == 404)
conferir('admin A não edita o cliente de B (404)', req('PATCH', f'/users/{id_b}/', {'nome': 'X'}, tk_a).status_code == 404)
conferir('admin A só vê a própria barbearia', req('GET', '/barbershops/', token=tk_a).json().get('count') == 1)
conferir('admin A não cria conta com o e-mail do cliente de B, em outra caixa (400)',
         req('POST', '/users/', {'email': f'CLIENTE.B.{S}@EXEMPLO.TEST', 'nome': 'X', 'password': SENHA, 'tipo_perfil': 'cliente'}, tk_a).status_code == 400)
conferir('agendamentos de A não incluem os de outras barbearias', req('GET', '/appointments/', token=tk_a).json().get('count') == 0)

# Edição de e-mail pelo próprio cliente (entrando com outra caixa).
st, tk_ca = token(f'CLIENTE.A.{S}@EXEMPLO.TEST')
conferir('login do cliente A com outra caixa', st == 200, str(st))
r = req('PATCH', f'/users/{id_a}/', {'email': f'Novo.A.{S}@Exemplo.Test'}, tk_ca)
conferir('edição do próprio e-mail grava a forma canônica', r.status_code == 200 and r.json().get('email') == f'novo.a.{S}@exemplo.test', str(r.status_code))
r = req('PATCH', f'/users/{id_a}/', {'email': f'Cliente.B.{S}@exemplo.test'}, tk_ca)
conferir('edição para o e-mail de outra conta, em outra caixa: 400 de duplicidade', r.status_code == 400 and 'email' in r.json(), str(r.status_code))
r = req('PATCH', f'/users/{id_a}/', {'email': f'novo.a.{S}@exémplo.test'}, tk_ca)
conferir('edição para e-mail não ASCII: 400', r.status_code == 400, str(r.status_code))
for invalido in ['a b@exemplo.test', f'x@exem​plo.test', 'x@İ.test', 123]:
    conferir(f'cadastro com e-mail inválido recusado ({invalido!r})',
             req('POST', '/auth/register/', {'nome': 'X', 'email': invalido, 'password': SENHA}).status_code == 400)

# Recuperação de senha seguida até a troca (o limite de login é 5/min: espera a janela).
time.sleep(61)
antes = set(os.listdir(MAIL))
r = req('POST', '/auth/password/reset/', {'email': f'  NOVO.A.{S}@EXEMPLO.TEST '})
conferir('pedido de recuperação com outra caixa e espaços: 204', r.status_code == 204, str(r.status_code))
time.sleep(0.5)
novos = sorted(set(os.listdir(MAIL)) - antes)
texto = open(os.path.join(MAIL, novos[-1]), encoding='utf-8').read() if novos else ''
para = re.findall(r'^To: (.*)$', texto, re.M)
uid = (re.search(r'^uid: (\S+)$', texto, re.M) or [None, ''])[1]
tok = (re.search(r'^token: (\S+)$', texto, re.M) or [None, ''])[1]
conta = int(base64.urlsafe_b64decode(uid + '=' * (-len(uid) % 4)).decode()) if uid else None
conferir('e-mail de recuperação capturado localmente, para o endereço canônico da própria conta',
         para == [f'novo.a.{S}@exemplo.test'] and conta == id_a, f'mensagens={len(novos)} conta_confere={conta == id_a}')
r = req('POST', '/auth/password/reset/confirm/', {'uid': uid, 'token': tok, 'new_password': NOVA})
conferir('confirmação com o token recebido: 204', r.status_code == 204, str(r.status_code))
conferir('login com a senha nova (outra caixa): 200', token(f'Novo.A.{S}@exemplo.test', NOVA)[0] == 200)
conferir('login com a senha antiga: 401', token(f'novo.a.{S}@exemplo.test', SENHA)[0] == 401)
r = req('POST', '/auth/password/reset/', {'email': f'inexistente.{S}@exemplo.test'})
conferir('recuperação de e-mail inexistente: 204', r.status_code == 204)
print('RESULTADO:', 'OK' if not falhas else f'{len(falhas)} falha(s): {falhas}')
sys.exit(1 if falhas else 0)
