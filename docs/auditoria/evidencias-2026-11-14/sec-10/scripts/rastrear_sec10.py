"""
SEC-10 — rastreamento de GET /appointments/available-slots/?exclude_appointment_id=… e do PER-13 (GET /users/{id}/),
com as consultas SQL de cada pedido. SQLite em memória (config.test_settings), sem banco real.
Uso, de dentro do diretório do código:  DEBUG=True python rastrear_sec10.py <rótulo>
"""
import os, re, sys
sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
import django
django.setup()
from datetime import time, timedelta
from django.db import connection
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext, setup_test_environment
from django.utils import timezone
setup_test_environment()
runner = DiscoverRunner(verbosity=0)
antigo = runner.setup_databases()
from rest_framework.test import APIClient
from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service

quando = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
def tenant(nome):
    s = Barbershop.objects.create(nome=f'Barbearia {nome}', endereco='R', telefone='1', email=f'{nome}@x.test', horario_abertura=time(8), horario_fechamento=time(18))
    u = lambda p, r: User.objects.create_user(email=f'{r}@{nome}.test', nome=f'{r} {nome}', password='Senha-segura-123', tipo_perfil=p, barbershop=s)
    t = dict(shop=s, admin=u('admin', 'admin'), cliente=u('cliente', 'cliente'), cliente2=u('cliente', 'cliente2'))
    t['barbeiro'] = Barber.objects.create(user=u('barbeiro', 'barbeiro'), barbershop=s)
    t['servico'] = Service.objects.create(barbershop=s, nome=f'Corte {nome}', preco='50.00', duracao=30)
    t['agend'] = Appointment.objects.create(barbershop=s, cliente=t['cliente'], barbeiro=t['barbeiro'], servico=t['servico'], data_hora=quando, preco_historico='50.00')
    return t
A, B = tenant('alfa'), tenant('beta')
print(f'### {sys.argv[1]}  (agendamento de A = {A["agend"].pk}, de B = {B["agend"].pk})')
api = APIClient(); api.force_authenticate(A['cliente'])
base = {'barbeiro': A['barbeiro'].pk, 'servico': A['servico'].pk, 'data': quando.date().isoformat()}
casos = [('1 próprio (A)', A['agend'].pk), ('2 outra barbearia (B)', B['agend'].pk), ('3 inexistente', 999999), ('4 omitido', None),
         ('5 malformado "abc"', 'abc'), ('5 malformado "1.5"', '1.5'), ('5 malformado "-1"', '-1'), ('5 vazio ""', ''),
         ('5 enorme 99999999999999999999', '99999999999999999999')]
for nome, valor in casos:
    params = dict(base) if valor is None else {**base, 'exclude_appointment_id': valor}
    with CaptureQueriesContext(connection) as q:
        r = api.get('/api/v1/appointments/available-slots/', params)
    corpo = r.content.decode()[:150]
    tem10 = ('"10:00"' in corpo) if r.status_code == 200 else None
    print(f'\n[{nome}] {r.status_code} {corpo}  | 10:00 livre? {tem10}')
    for c in q.captured_queries:
        if 'appointments_appointment' in c['sql'] and (' WHERE ' in c['sql']):
            onde = c['sql'].split(' WHERE ', 1)[1][:170]
            joins = re.findall(r'JOIN "(\w+)"', c['sql'])
            alheio = ' <<< LÊ O AGENDAMENTO DE OUTRA BARBEARIA SEM CONDIÇÃO DE BARBEARIA' if re.search(rf'"appointments_appointment"\."id" = {B["agend"].pk}\b', c['sql']) and 'barbershop_id" =' not in onde else ''
            print(f'   - appointments_appointment (joins: {joins}) WHERE {onde}{alheio}')
print('\n### PER-13: GET /users/{id}/ como cliente de A')
for nome, alvo in (('outro cliente de A', A['cliente2'].pk), ('usuário de B', B['cliente'].pk), ('inexistente', 999999)):
    r = api.get(f'/api/v1/users/{alvo}/')
    print(f'[{nome}] {r.status_code} {r.content.decode()[:120]}')
runner.teardown_databases(antigo)
