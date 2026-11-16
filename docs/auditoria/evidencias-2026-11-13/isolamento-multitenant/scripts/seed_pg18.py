"""
Popula o banco DESCARTÁVEL da auditoria (PG18 descartável do smoke test, porta 55432).
Todos os dados são fictícios. Senhas aleatórias ficam só no scratchpad.
Uso: DJANGO_SETTINGS_MODULE=audit_server_settings python seed.py <arquivo_credenciais.json>
"""
import json
import os
import random
import secrets
import sys
from datetime import datetime, time, timedelta
from decimal import Decimal

import django

django.setup()

from django.conf import settings  # noqa: E402
from django.utils import timezone  # noqa: E402

assert settings.DATABASES['default']['PORT'] == '55432', 'Recusa: só roda no banco descartável'

from accounts.models import User  # noqa: E402
from appointments.models import Appointment  # noqa: E402
from barbershops.models import Barber, Barbershop  # noqa: E402
from services.models import Service  # noqa: E402

random.seed(42)
creds = {}


def pwd():
    return 'Aud-' + secrets.token_urlsafe(12)


def user(email, nome, perfil, shop, **extra):
    p = pwd()
    u = User.objects.create_user(email=email, nome=nome, password=p, tipo_perfil=perfil, barbershop=shop, **extra)
    creds[email] = p
    return u


def local(day_offset, hh, mm=0):
    d = timezone.localdate() + timedelta(days=day_offset)
    return timezone.make_aware(datetime.combine(d, time(hh, mm)))


shop_a = Barbershop.objects.create(
    nome='Barbearia Navalha Fictícia', endereco='Rua Exemplo, 100', telefone='11900000000',
    email='contato@navalha.exemplo.test', horario_abertura=time(9), horario_fechamento=time(19),
)
shop_b = Barbershop.objects.create(
    nome='Barbearia Outra Fictícia', endereco='Av. Teste, 200', telefone='21900000000',
    email='contato@outra.exemplo.test', horario_abertura=time(8), horario_fechamento=time(18),
)

admin_a = user('admin.a@exemplo.test', 'Ana Proprietária', 'admin', shop_a)
b_users = [
    user('joao.barbeiro@exemplo.test', 'João Navalha', 'barbeiro', shop_a),
    user('pedro.barbeiro@exemplo.test', 'Pedro Tesoura', 'barbeiro', shop_a),
    user('caio.barbeiro@exemplo.test', 'Caio Pente', 'barbeiro', shop_a),
]
barbers = [Barber.objects.create(user=u, barbershop=shop_a, especialidade=esp)
           for u, esp in zip(b_users, ['Degradê', 'Barba', 'Clássicos'])]
clientes = [
    user(f'cliente{i}@exemplo.test', nome, 'cliente', shop_a)
    for i, nome in enumerate(['Bruno Cliente', 'Carla Cliente', 'Diego Cliente', 'Elisa Cliente',
                              'Fábio Cliente', 'Gabriel Cliente'], start=1)
]
svc = [
    Service.objects.create(barbershop=shop_a, nome='Corte', preco=Decimal('45.00'), duracao=30),
    Service.objects.create(barbershop=shop_a, nome='Barba', preco=Decimal('35.00'), duracao=30),
    Service.objects.create(barbershop=shop_a, nome='Corte + Barba', preco=Decimal('70.00'), duracao=60),
    Service.objects.create(barbershop=shop_a, nome='Pigmentação', preco=Decimal('90.00'), duracao=90),
]
inactive_svc = Service.objects.create(barbershop=shop_a, nome='Relaxamento (inativo)', preco=Decimal('80.00'),
                                      duracao=60, ativo=False)

admin_b = user('admin.b@exemplo.test', 'Beatriz Proprietária B', 'admin', shop_b)
bb_user = user('barbeiro.b@exemplo.test', 'Bento Barbeiro B', 'barbeiro', shop_b)
barber_b = Barber.objects.create(user=bb_user, barbershop=shop_b, especialidade='Corte')
cliente_b = user('cliente.b@exemplo.test', 'Clara Cliente B', 'cliente', shop_b)
svc_b = Service.objects.create(barbershop=shop_b, nome='Corte B', preco=Decimal('50.00'), duracao=30)

sp = pwd()
superuser = User.objects.create_superuser(email='plataforma@exemplo.test', nome='Operador Plataforma', password=sp)
creds['plataforma@exemplo.test'] = sp

# Histórico (gravado direto pelo ORM, sem full_clean, como um passado real).
created = 0
for day in range(-30, 0):
    for b in barbers:
        hour = 9
        while hour < 18:
            if random.random() < 0.45:
                s = random.choice(svc[:3])
                st = random.choices(['realizado', 'cancelado', 'agendado'], weights=[85, 10, 5])[0]
                Appointment.objects.create(
                    barbershop=shop_a, cliente=random.choice(clientes), barbeiro=b, servico=s,
                    data_hora=local(day, hour), status=st, preco_historico=s.preco,
                )
                created += 1
            hour += 1
# Hoje e próximos dias (agendado/confirmado).
for day in range(0, 8):
    for b in barbers:
        for hour in (10, 11, 14, 15, 16):
            if random.random() < 0.5:
                s = random.choice(svc[:3])
                st = random.choice(['agendado', 'confirmado'])
                Appointment.objects.create(
                    barbershop=shop_a, cliente=random.choice(clientes), barbeiro=b, servico=s,
                    data_hora=local(day, hour), status=st, preco_historico=s.preco,
                )
                created += 1
# Um atendimento noturno realizado ontem às 22:30 (para verificar o agrupamento diário em UTC).
Appointment.objects.create(
    barbershop=shop_a, cliente=clientes[0], barbeiro=barbers[0], servico=svc[0],
    data_hora=local(-1, 22, 30), status='realizado', preco_historico=svc[0].preco,
)
Appointment.objects.create(
    barbershop=shop_b, cliente=cliente_b, barbeiro=barber_b, servico=svc_b,
    data_hora=local(2, 10), status='agendado', preco_historico=svc_b.preco,
)

ids = {
    'shop_a': shop_a.pk, 'shop_b': shop_b.pk, 'admin_a': admin_a.pk, 'admin_b': admin_b.pk,
    'barbers': [b.pk for b in barbers], 'barber_users': [u.pk for u in b_users], 'barber_b': barber_b.pk,
    'clientes': [c.pk for c in clientes], 'cliente_b': cliente_b.pk, 'services': [s.pk for s in svc],
    'inactive_service': inactive_svc.pk, 'service_b': svc_b.pk, 'superuser': superuser.pk,
}
with open(sys.argv[1], 'w') as fh:
    json.dump({'creds': creds, 'ids': ids}, fh, indent=1)
print(f'seed ok: {created + 2} agendamentos, {User.objects.count()} usuários')
