from datetime import time, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from .models import Appointment


class AppointmentSecurityTests(APITestCase):
    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.client_user = self.create_user(
            'cliente@example.com', User.TipoPerfil.CLIENTE
        )
        self.other_client = self.create_user(
            'outro-cliente@example.com', User.TipoPerfil.CLIENTE
        )
        barber_user = self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte',
            preco='50.00',
            duracao=30,
        )
        self.start = (timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0)
        self.existing_appointment = self.create_appointment(self.start)
        self.client.force_authenticate(self.client_user)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def create_appointment(self, data_hora):
        return Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=data_hora,
        )

    def appointment_payload(self, data_hora):
        return {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': data_hora.isoformat(),
        }

    def test_api_rejects_overlapping_appointments_on_create_and_update(self):
        create_response = self.client.post(
            reverse('appointment-list'),
            self.appointment_payload(self.start + timedelta(minutes=15)),
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', create_response.data)

        later_appointment = self.create_appointment(self.start + timedelta(minutes=60))
        update_response = self.client.patch(
            reverse('appointment-detail', args=[later_appointment.pk]),
            {'data_hora': (self.start + timedelta(minutes=15)).isoformat()},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', update_response.data)
        later_appointment.refresh_from_db()
        self.assertEqual(later_appointment.data_hora, self.start + timedelta(minutes=60))

    def test_client_cannot_transfer_own_appointment(self):
        response = self.client.patch(
            reverse('appointment-detail', args=[self.existing_appointment.pk]),
            {'cliente': self.other_client.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)
        self.existing_appointment.refresh_from_db()
        self.assertEqual(self.existing_appointment.cliente_id, self.client_user.pk)
