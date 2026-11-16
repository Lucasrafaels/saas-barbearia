"""
TEN-03 — SIMULAÇÃO DE LABORATÓRIO da Alternativa C ("esconder a mensagem" e "padronizar status e corpo"), sem
alterar o projeto: as variações são aplicadas só neste processo (mock / override_settings) e cada cenário roda dentro
de uma transação desfeita no fim, no banco DESCARTÁVEL t3_lab (PG 18.3, 127.0.0.1:55432).

Pergunta: com a mensagem genérica, ou com status e corpo idênticos para qualquer erro de validação, ainda dá para
distinguir e-mail cadastrado (em outra barbearia) de e-mail livre?
Uso: DJANGO_SETTINGS_MODULE=t3_lab_settings python t3_simulacao_alt_c.py <saida.json>
"""
import json
import sys
from contextlib import ExitStack
from datetime import time
from unittest import mock

import django

django.setup()
from django.conf import settings  # noqa: E402
from django.db import transaction  # noqa: E402
from django.test import override_settings  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

assert settings.DATABASES['default']['NAME'] == 't3_lab' and settings.DATABASES['default']['PORT'] == '55432'

from accounts.models import User  # noqa: E402
from barbershops.models import Barbershop  # noqa: E402

SENHA = 'Navalha-Fict-2026!'
FRACA = '12345678'
GENERICA = 'Não foi possível usar este e-mail.'


class Desfazer(Exception):
    pass


def seed():
    a = Barbershop.objects.create(nome='Alfa Lab', endereco='x', telefone='1', email='c@alfa.test',
                                  horario_abertura=time(9), horario_fechamento=time(19))
    b = Barbershop.objects.create(nome='Beta Lab', endereco='x', telefone='2', email='c@beta.test',
                                  horario_abertura=time(9), horario_fechamento=time(19))
    admin_a = User.objects.create_user(email='admin.a@alfa.test', nome='Ana', password=SENHA, tipo_perfil='admin', barbershop=a)
    cli_a = User.objects.create_user(email='cliente.a1@alfa.test', nome='Carlos', password=SENHA, tipo_perfil='cliente', barbershop=a)
    User.objects.create_user(email='cliente.b@beta.test', nome='Clara', password=SENHA, tipo_perfil='cliente', barbershop=b)
    return admin_a, cli_a


PARES = [
    # (id, fluxo, papel, método, caminho, corpo com {email})
    ('S1', 'cadastro público, senha válida', None, 'post', '/api/v1/auth/register/', {'nome': 'Rita', 'password': SENHA}),
    ('S2', 'cadastro público, senha fraca (sem efeito colateral)', None, 'post', '/api/v1/auth/register/', {'nome': 'Rita', 'password': FRACA}),
    ('S3', 'admin A cria cliente, senha válida', 'admin', 'post', '/api/v1/users/', {'nome': 'Caio', 'password': SENHA, 'tipo_perfil': 'cliente'}),
    ('S4', 'admin A cria cliente, senha fraca', 'admin', 'post', '/api/v1/users/', {'nome': 'Caio', 'password': FRACA, 'tipo_perfil': 'cliente'}),
    ('S5', 'cliente A1 troca o próprio e-mail', 'cliente', 'patch', '/api/v1/users/{self}/', {}),
    ('S6', 'cliente A1 troca o próprio e-mail + nome vazio', 'cliente', 'patch', '/api/v1/users/{self}/', {'nome': ''}),
]
EMAILS = {'existente_em_B': 'cliente.b@beta.test', 'livre': 'livre.{sid}@exemplo.test',
          'existente_em_B_dominio_maiusculo': 'cliente.b@BETA.TEST', 'livre_dominio_maiusculo': 'livre.{sid}@EXEMPLO.TEST'}

VARIANTES = {
    'atual': [],
    'C1_so_mensagem_generica': [lambda: mock.patch.dict(User._meta.get_field('email').error_messages, {'unique': GENERICA})],
    'C2_status_e_corpo_padronizados_em_todo_400': [
        lambda: mock.patch.dict(User._meta.get_field('email').error_messages, {'unique': GENERICA}),
        lambda: override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'EXCEPTION_HANDLER': 't3_lab_handlers.handler_generico'}),
    ],
}


def rodar(variante, patches):
    saida = []
    for sid, fluxo, papel, metodo, caminho, corpo in PARES:
        linha = {'variante': variante, 'id': sid, 'fluxo': fluxo, 'respostas': {}}
        for rotulo, molde in EMAILS.items():
            email = molde.format(sid=sid.lower())
            try:
                with ExitStack() as pilha, transaction.atomic():
                    for p in patches:
                        pilha.enter_context(p())
                    admin_a, cli_a = seed()
                    antes = User.objects.count()
                    c = APIClient()
                    c.raise_request_exception = False
                    if papel == 'admin':
                        c.force_authenticate(admin_a)
                    elif papel == 'cliente':
                        c.force_authenticate(cli_a)
                    r = getattr(c, metodo)(caminho.format(self=cli_a.pk), {**corpo, 'email': email}, format='json')
                    try:
                        criado = User.objects.count() - antes
                        alterado = User.objects.filter(pk=cli_a.pk, email=email).exists() if papel == 'cliente' else None
                    except Exception:
                        criado, alterado = 'transação abortada pelo erro do banco', None
                    corpo_r = r.content.decode()
                    linha['respostas'][rotulo] = {
                        'email': email, 'status': r.status_code,
                        'corpo': corpo_r if r.status_code != 500 else 'HTML "Server Error (500)"',
                        'contas_criadas': criado, 'email_do_proprio_alterado': alterado}
                    raise Desfazer
            except Desfazer:
                pass
        ex, lv = linha['respostas']['existente_em_B'], linha['respostas']['livre']
        exm, lvm = linha['respostas']['existente_em_B_dominio_maiusculo'], linha['respostas']['livre_dominio_maiusculo']
        norm = lambda x: (x['status'], x['corpo'].replace(x['email'], '<e-mail>'))  # noqa: E731
        linha['distingue_existente_de_livre'] = norm(ex)[0] != norm(lv)[0] or (norm(ex)[1] != norm(lv)[1] and ex['status'] != 201)
        linha['distingue_pela_variacao_de_caixa_no_dominio'] = exm['status'] != lvm['status']
        saida.append(linha)
        print(f"{variante:45} {sid} {fluxo:52} existente={ex['status']} {ex['corpo'][:70]!r:72} livre={lv['status']} {lv['corpo'][:70]!r:72} "
              f"| distingue={linha['distingue_existente_de_livre']} | domínio maiúsculo: {exm['status']} x {lvm['status']}")
    return saida


resultado = []
for nome, patches in VARIANTES.items():
    resultado += rodar(nome, patches)
assert User.objects.count() == 0, 'o banco de laboratório deveria continuar vazio'
json.dump(resultado, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
