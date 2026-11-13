"""
Verificações pelo ORM no banco DESCARTÁVEL (porta 55433):
  modo 'duracao0'  -> serviço com duração 0 e consulta de horários (rodar com `timeout`)
  modo 'queries'   -> nº de consultas SQL por endpoint (N+1)
"""
import sys
from datetime import date, timedelta

import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['PORT'] == '55433'

from django.db import connection  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from accounts.models import User  # noqa: E402
from barbershops.models import Barber  # noqa: E402
from services.models import Service  # noqa: E402

settings.ALLOWED_HOSTS = ['*']
mode = sys.argv[1]
admin = User.objects.get(email='admin.a@exemplo.test')
cliente = User.objects.get(email='cliente1@exemplo.test')
barber = Barber.objects.filter(barbershop=admin.barbershop, ativo=True).first()

if mode == 'duracao0':
    svc = Service.objects.create(barbershop=admin.barbershop, nome='Duração zero (Django Admin)', preco='10.00', duracao=0)
    c = APIClient(); c.force_authenticate(cliente)
    d = (date.today() + timedelta(days=20)).isoformat()
    print('chamando available-slots com duracao=0 ...', flush=True)
    r = c.get('/api/v1/appointments/available-slots/', {'barbeiro': barber.pk, 'servico': svc.pk, 'data': d})
    print('respondeu', r.status_code)
elif mode == 'queries':
    rows = []
    for who, paths in ((admin, ['/api/v1/appointments/', '/api/v1/users/', '/api/v1/services/?ativo=all', '/api/v1/barbers/?ativo=all',
                                '/api/v1/appointments/revenue-report/', '/api/v1/barbershops/']),
                       (cliente, ['/api/v1/appointments/', '/api/v1/barbers/', '/api/v1/services/',
                                  f'/api/v1/appointments/available-slots/?barbeiro={barber.pk}&servico={Service.objects.filter(barbershop=admin.barbershop, ativo=True).first().pk}&data={(date.today()+timedelta(days=3)).isoformat()}'])):
        c = APIClient(); c.force_authenticate(who)
        with CaptureQueriesContext(connection) as ctx:
            r = c.get(path) if False else None
        for path in paths:
            with CaptureQueriesContext(connection) as ctx:
                r = c.get(path)
            n = len(r.data.get('results', [])) if isinstance(r.data, dict) and 'results' in r.data else '-'
            rows.append(f'{who.tipo_perfil:8} GET {path.split("?")[0]:45} HTTP {r.status_code}  itens={n!s:>3}  consultas SQL={len(ctx.captured_queries)}')
    print('\n'.join(rows))
