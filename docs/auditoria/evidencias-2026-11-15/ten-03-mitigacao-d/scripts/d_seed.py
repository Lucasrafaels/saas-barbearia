"""Seed fictício do banco DESCARTÁVEL D_DB e emissão de tokens de acesso (sem passar pelo login, para não gastar
a cota de login da sondagem). Uso: D_DB=... DJANGO_SETTINGS_MODULE=d_settings python d_seed.py <estado.json>"""
import json
import secrets
import sys
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['PORT'] == '55432' and settings.DATABASES['default']['NAME'].startswith('d_')
from rest_framework_simplejwt.tokens import AccessToken  # noqa: E402

from accounts.models import User  # noqa: E402
from barbershops.models import Barbershop  # noqa: E402

a = Barbershop.objects.create(nome='Alfa Fictícia', endereco='Rua Exemplo, 1', telefone='11900000001', email='contato@alfa.test',
                              horario_abertura=time(9), horario_fechamento=time(19))
b = Barbershop.objects.create(nome='Beta Fictícia', endereco='Rua Exemplo, 2', telefone='11900000002', email='contato@beta.test',
                              horario_abertura=time(9), horario_fechamento=time(19))
estado = {'creds': {}, 'ids': {}, 'tokens': {}}
for chave, email, nome, perfil, shop in [
    ('admin_a', 'admin.a@alfa.test', 'Ana Admin A', 'admin', a),
    ('cliente_a1', 'cliente.a1@alfa.test', 'Carlos Cliente A1', 'cliente', a),
    ('cliente_a2', 'cliente.a2@alfa.test', 'Celia Cliente A2', 'cliente', a),
    ('admin_b', 'admin.b@beta.test', 'Beatriz Admin B', 'admin', b),
    ('cliente_b', 'cliente.b@beta.test', 'Clara Cliente B', 'cliente', b),
]:
    senha = 'D-' + secrets.token_urlsafe(12)
    u = User.objects.create_user(email=email, nome=nome, password=senha, tipo_perfil=perfil, barbershop=shop)
    estado['creds'][chave] = {'email': email, 'password': senha}
    estado['ids'][chave] = u.pk
    estado['tokens'][chave] = str(AccessToken.for_user(u))
json.dump(estado, open(sys.argv[1], 'w'), indent=1)
print('seed ok', settings.DATABASES['default']['NAME'], User.objects.count())
