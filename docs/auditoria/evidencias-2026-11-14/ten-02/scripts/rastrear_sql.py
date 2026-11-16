"""
TEN-02 — rastreamento das consultas SQL de um usuário SEM barbearia ao tentar agendar com o barbeiro de outra
barbearia (B). Roda em SQLite em memória (config.test_settings), sem banco real. Uso, de dentro do diretório do
código a examinar:  DEBUG=True python rastrear_sql.py <rótulo> [--escopo-amplo]
--escopo-amplo simula uma mudança futura que libere os campos relacionais para a conta sem barbearia
(substitui config.tenancy.barbearia_do_pedido por "todas as barbearias"); só existe no código com config/tenancy.py.
"""
import os, re, sys
sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
import django
django.setup()
from datetime import time, timedelta
from unittest import mock
from django.db import connection
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext, setup_test_environment
from django.utils import timezone

rotulo, amplo = sys.argv[1], '--escopo-amplo' in sys.argv
setup_test_environment()
runner = DiscoverRunner(verbosity=0)
antigo = runner.setup_databases()
from rest_framework.test import APIClient
from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service

b = Barbershop.objects.create(nome='Barbearia Beta', endereco='R', telefone='1', email='b@b.test', horario_abertura=time(8), horario_fechamento=time(18))
cliente_b = User.objects.create_user(email='c@b.test', nome='Cliente Beta', password='Senha-segura-123', tipo_perfil='cliente', barbershop=b)
barbeiro_b = Barber.objects.create(user=User.objects.create_user(email='bb@b.test', nome='Barbeiro Beta', password='Senha-segura-123', tipo_perfil='barbeiro', barbershop=b), barbershop=b)
servico_b = Service.objects.create(barbershop=b, nome='Corte Beta', preco='50.00', duracao=30)
ocupado = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
Appointment.objects.create(barbershop=b, cliente=cliente_b, barbeiro=barbeiro_b, servico=servico_b, data_hora=ocupado, preco_historico='50.00')
sem = User.objects.create_user(email='sem@publico.test', nome='Conta Publica', password='Senha-segura-123')
api = APIClient(); api.force_authenticate(sem)
casos = {
    '1 horário ocupado de B': {'cliente': cliente_b.pk, 'barbeiro': barbeiro_b.pk, 'servico': servico_b.pk, 'data_hora': ocupado.isoformat()},
    '2 horário livre de B': {'cliente': cliente_b.pk, 'barbeiro': barbeiro_b.pk, 'servico': servico_b.pk, 'data_hora': (ocupado + timedelta(hours=4)).isoformat()},
    '3 barbeiro de B (válido), sem os demais campos de B': {'cliente': sem.pk, 'barbeiro': barbeiro_b.pk, 'servico': servico_b.pk, 'data_hora': ocupado.isoformat()},
    '4 IDs inexistentes': {'cliente': 999999, 'barbeiro': 999999, 'servico': 999999, 'data_hora': ocupado.isoformat()},
}
contexto = mock.patch('config.tenancy.barbearia_do_pedido', side_effect=lambda *a, **k: __import__('config.tenancy', fromlist=['x']).TODAS_AS_BARBEARIAS) if amplo else mock.patch('os.getcwd', os.getcwd)
print(f'### {rotulo}{" (escopo dos campos ampliado: simulação)" if amplo else ""}')
with contexto:
    for nome, corpo in casos.items():
        antes = Appointment.objects.count()
        with CaptureQueriesContext(connection) as q:
            r = api.post('/api/v1/appointments/', corpo, format='json')
        print(f'\n[{nome}] {r.status_code} {r.content.decode()[:240]}')
        print(f'   agendamentos criados: {Appointment.objects.count() - antes}; consultas: {len(q.captured_queries)}')
        for c in q.captured_queries:
            sql = c['sql']
            tabela = re.search(r'FROM "(\w+)"', sql)
            onde = sql.split(' WHERE ', 1)[1][:150] if ' WHERE ' in sql else ''
            marca = '  <<< DISPONIBILIDADE (agenda do barbeiro)' if tabela and tabela.group(1) == 'appointments_appointment' else ''
            print(f'   - {tabela.group(1) if tabela else sql[:40]}: WHERE {onde}{marca}')
runner.teardown_databases(antigo)
