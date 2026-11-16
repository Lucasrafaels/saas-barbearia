"""
PER-13 — mapa de respostas e SQL de /users/{id}/ por papel e método. SQLite em memória (config.test_settings), sem
banco real. Uso, de dentro do diretório do código:  DEBUG=True python rastrear_per13.py <rótulo>
"""
import os, re, sys
sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
import django
django.setup()
from datetime import time
from django.db import connection
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext, setup_test_environment
setup_test_environment()
runner = DiscoverRunner(verbosity=0)
antigo = runner.setup_databases()
from rest_framework.test import APIClient
from accounts.models import User
from barbershops.models import Barber, Barbershop

def tenant(n):
    s = Barbershop.objects.create(nome=f'Barbearia {n}', endereco='R', telefone='1', email=f'{n}@x.test', horario_abertura=time(8), horario_fechamento=time(18))
    u = lambda p, r: User.objects.create_user(email=f'{r}@{n}.test', nome=f'{r} {n}', password='Senha-segura-123', tipo_perfil=p, barbershop=s)
    t = dict(admin=u('admin', 'admin'), cliente=u('cliente', 'cliente'), cliente2=u('cliente', 'cliente2'))
    t['barbeiro'] = u('barbeiro', 'barbeiro'); Barber.objects.create(user=t['barbeiro'], barbershop=s)
    t['barbeiro2'] = u('barbeiro', 'barbeiro2'); Barber.objects.create(user=t['barbeiro2'], barbershop=s)
    return t
A, B = tenant('alfa'), tenant('beta')
sem = User.objects.create_user(email='sem@publico.test', nome='Conta Publica', password='Senha-segura-123')
su = User.objects.create_superuser(email='op@plataforma.test', nome='Operador', password='Senha-segura-123')
print(f'### {sys.argv[1]}')
papeis = [('cliente A', A['cliente']), ('barbeiro A', A['barbeiro']), ('admin A', A['admin']), ('sem barbearia', sem), ('superusuário', su)]
alvos = lambda eu: [('o próprio', eu.pk), ('cliente2 A', A['cliente2'].pk), ('barbeiro2 A', A['barbeiro2'].pk), ('admin A', A['admin'].pk),
                    ('cliente B', B['cliente'].pk), ('inexistente', 999999)]
for nome, eu in papeis:
    api = APIClient(); api.force_authenticate(eu)
    print(f'\n== {nome} (id {eu.pk})')
    for rot, alvo in alvos(eu):
        linha = []
        for metodo in ('get', 'head', 'patch', 'put', 'delete'):
            with CaptureQueriesContext(connection) as q:
                if metodo in ('patch', 'put'):
                    r = getattr(api, metodo)(f'/api/v1/users/{alvo}/', {'nome': 'Sondagem'} if metodo == 'patch' else {}, format='json')
                else:
                    r = getattr(api, metodo)(f'/api/v1/users/{alvo}/')
            linha.append(f'{metodo.upper()} {r.status_code}')
            if metodo == 'get':
                corpo = r.content.decode()[:70]
                onde = [c['sql'].split(' WHERE ', 1)[1][:110] for c in q.captured_queries if 'accounts_user' in c['sql'] and ' WHERE ' in c['sql']]
        print(f'   {rot:12} | {" | ".join(linha)} | GET corpo: {corpo} | SQL: {onde}')
        # Desfaz qualquer escrita aceita (PATCH/PUT/DELETE do admin ou do próprio), para não contaminar as próximas linhas.
        User.objects.filter(pk=alvo).update(nome=User.objects.filter(pk=alvo).values_list('email', flat=True).first() or '', is_active=True)
runner.teardown_databases(antigo)
