"""AUTH-04/05: seed fictício do banco DESCARTÁVEL a45_db, com tokens de acesso emitidos direto (sem gastar login).
Uso: H_DB=<banco> DJANGO_SETTINGS_MODULE=h_settings python a45_seed.py <estado.json>"""
import json
import secrets
import sys
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['NAME'] in ('h_novo_f', 'h_novo_t', 'h_ant_f') and settings.DATABASES['default']['PORT'] == '55432'
from rest_framework_simplejwt.tokens import AccessToken  # noqa: E402

from accounts.models import User  # noqa: E402
from barbershops.models import Barbershop  # noqa: E402

a = Barbershop.objects.create(nome='Alfa Fictícia', endereco='Rua Exemplo, 1', telefone='11900000001', email='contato@alfa.test',
                              horario_abertura=time(9), horario_fechamento=time(19))
b = Barbershop.objects.create(nome='Beta Fictícia', endereco='Rua Exemplo, 2', telefone='11900000002', email='contato@beta.test',
                              horario_abertura=time(9), horario_fechamento=time(19))
estado = {'creds': {}, 'ids': {}, 'tokens': {}, 'shops': {'A': a.pk, 'B': b.pk}}
for chave, email, nome, perfil, shop in [
    ('admin_a', 'admin.a@alfa.test', 'Ana Admin A', 'admin', a),
    ('cliente_a1', 'cliente.a1@alfa.test', 'Carlos Cliente A1', 'cliente', a),
    ('cliente_a2', 'cliente.a2@alfa.test', 'Celia Cliente A2', 'cliente', a),
    ('admin_b', 'admin.b@beta.test', 'Beatriz Admin B', 'admin', b),
    ('cliente_b', 'cliente.b@beta.test', 'Clara Cliente B', 'cliente', b),
]:
    senha = 'A45-' + secrets.token_urlsafe(12)
    u = User.objects.create_user(email=email, nome=nome, password=senha, tipo_perfil=perfil, barbershop=shop)
    estado['creds'][chave] = {'email': email, 'password': senha}
    estado['ids'][chave] = u.pk
    estado['tokens'][chave] = str(AccessToken.for_user(u))
json.dump(estado, open(sys.argv[1], 'w'), indent=1)
print('seed ok', User.objects.count(), 'usuários')
