#!/usr/bin/env python
"""Debug script to see the actual 400 error response"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from appointments.models import Appointment
from datetime import time, datetime, timedelta
from django.utils import timezone
from decimal import Decimal

# Create test data
shop_a = Barbershop.objects.create(
    nome='Barbearia A', endereco='Rua A, 100', telefone='11900000001',
    email='a@example.com', horario_abertura=time(8), horario_fechamento=time(18)
)
shop_b = Barbershop.objects.create(
    nome='Barbearia B', endereco='Rua B, 200', telefone='11900000002',
    email='b@example.com', horario_abertura=time(8), horario_fechamento=time(18)
)

admin_a = User.objects.create_user(
    email='admin-a@example.com', nome='Admin A', password='Senha-segura-123',
    tipo_perfil=User.TipoPerfil.ADMIN, barbershop=shop_a
)
barber_a = User.objects.create_user(
    email='barber-a@example.com', nome='Barber A', password='Senha-segura-123',
    tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=shop_a
)
client_a = User.objects.create_user(
    email='client-a@example.com', nome='Client A', password='Senha-segura-123',
    tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=shop_a
)

barber_profile_a = Barber.objects.create(user=barber_a, barbershop=shop_a, ativo=True)

service_a = Service.objects.create(
    barbershop=shop_a, nome='Service A', preco=Decimal('50.00'), duracao=30, ativo=True
)

future_date = (timezone.localtime() + timedelta(days=1)).date()
safe_data_hora = timezone.make_aware(datetime.combine(future_date, time(10, 0)))

appointment_a = Appointment.objects.create(
    barbershop=shop_a, cliente=client_a, barbeiro=barber_profile_a,
    servico=service_a, data_hora=safe_data_hora, status=Appointment.Status.AGENDADO
)

# Test 1: Barber A update
print("=" * 60)
print("TEST 1: Barber A updating own appointment (same tenant)")
print("=" * 60)
client = APIClient()
client.force_authenticate(barber_a)
url = f'/api/v1/appointments/{appointment_a.id}/'
payload = {'observacoes': 'Updated by Barber A'}
response = client.patch(url, payload, format='json')
print(f'Status: {response.status_code}')
print(f'Response: {response.data}')
print()

# Test 2: Client A update
print("=" * 60)
print("TEST 2: Client A updating own appointment (same tenant)")
print("=" * 60)
client = APIClient()
client.force_authenticate(client_a)
url = f'/api/v1/appointments/{appointment_a.id}/'
payload = {'observacoes': 'Updated by Client A'}
response = client.patch(url, payload, format='json')
print(f'Status: {response.status_code}')
print(f'Response: {response.data}')
print()

# Test 3: Superuser update
print("=" * 60)
print("TEST 3: Superuser updating appointment")
print("=" * 60)
superuser = User.objects.create_superuser(
    email='root@example.com', nome='Super User', password='Senha-segura-123'
)
client = APIClient()
client.force_authenticate(superuser)
url = f'/api/v1/appointments/{appointment_a.id}/'
payload = {'observacoes': 'Updated by Superuser'}
response = client.patch(url, payload, format='json')
print(f'Status: {response.status_code}')
print(f'Response: {response.data}')
print()

# Also check what appointment data looks like
print("=" * 60)
print("APPOINTMENT DATA")
print("=" * 60)
print(f'Appointment ID: {appointment_a.id}')
print(f'Appointment data_hora: {appointment_a.data_hora}')
print(f'Appointment status: {appointment_a.status}')
print(f'Now: {timezone.now()}')
print(f'Is in future: {appointment_a.data_hora > timezone.now()}')
print(f'Barber: {appointment_a.barbeiro}')
print(f'Barber active: {appointment_a.barbeiro.ativo}')
print(f'Service: {appointment_a.servico}')
print(f'Service active: {appointment_a.servico.ativo}')