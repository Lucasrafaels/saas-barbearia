"""
TEN-03: popula o banco DESCARTÁVEL t3_db (PG 18.3, 127.0.0.1:55432). Todos os dados são fictícios
(domínios reservados .test). As senhas são aleatórias e ficam só no scratchpad (arquivo 600).
Uso: DJANGO_SETTINGS_MODULE=t3_settings python t3_seed.py <estado.json>
"""
import json
import secrets
import sys
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['PORT'] == '55432' and settings.DATABASES['default']['NAME'] == 't3_db', 'Recusa: só roda no banco descartável'

from accounts.models import User  # noqa: E402
from barbershops.models import Barber, Barbershop  # noqa: E402

creds, ids = {}, {}


def user(chave, email, nome, perfil, shop, **extra):
    p = 'T3-' + secrets.token_urlsafe(12)
    u = User.objects.create_user(email=email, nome=nome, password=p, tipo_perfil=perfil, barbershop=shop, **extra)
    creds[chave] = {'email': email, 'password': p}
    ids[chave] = u.pk
    return u


shop_a = Barbershop.objects.create(nome='Barbearia Alfa Fictícia', endereco='Rua Exemplo, 1', telefone='11900000001',
                                   email='contato@alfa.test', horario_abertura=time(9), horario_fechamento=time(19))
shop_b = Barbershop.objects.create(nome='Barbearia Beta Fictícia', endereco='Rua Exemplo, 2', telefone='11900000002',
                                   email='contato@beta.test', horario_abertura=time(9), horario_fechamento=time(19))
ids['shop_a'], ids['shop_b'] = shop_a.pk, shop_b.pk

user('admin_a', 'admin.a@alfa.test', 'Ana Admin A', 'admin', shop_a)
ba = user('barbeiro_a', 'barbeiro.a@alfa.test', 'Bruno Barbeiro A', 'barbeiro', shop_a)
Barber.objects.create(user=ba, barbershop=shop_a, especialidade='Corte')
user('cliente_a1', 'cliente.a1@alfa.test', 'Carlos Cliente A1', 'cliente', shop_a)
user('cliente_a2', 'cliente.a2@alfa.test', 'Celia Cliente A2', 'cliente', shop_a)
user('admin_b', 'admin.b@beta.test', 'Beatriz Admin B', 'admin', shop_b)
bb = user('barbeiro_b', 'barbeiro.b@beta.test', 'Bento Barbeiro B', 'barbeiro', shop_b)
Barber.objects.create(user=bb, barbershop=shop_b, especialidade='Barba')
user('cliente_b', 'cliente.b@beta.test', 'Clara Cliente B', 'cliente', shop_b)
user('inativo_b', 'inativo.b@beta.test', 'Igor Inativo B', 'cliente', shop_b, is_active=False)
user('sem_barbearia', 'sem.barbearia@exemplo.test', 'Saulo Sem Barbearia', 'cliente', None)
sp = 'T3-' + secrets.token_urlsafe(12)
su = User.objects.create_superuser(email='plataforma@exemplo.test', nome='Operador Plataforma', password=sp)
creds['superuser'] = {'email': 'plataforma@exemplo.test', 'password': sp}
ids['superuser'] = su.pk

with open(sys.argv[1], 'w') as fh:
    json.dump({'creds': creds, 'ids': ids}, fh, indent=1)
print('seed ok:', User.objects.count(), 'usuários,', Barbershop.objects.count(), 'barbearias')
