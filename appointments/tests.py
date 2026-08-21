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
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN)
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

    def test_appointment_cliente_must_have_client_role(self):
        self.client.force_authenticate(self.admin)
        payload = self.appointment_payload(self.start + timedelta(minutes=60))
        payload['cliente'] = self.admin.pk

        response = self.client.post(reverse('appointment-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)

    def test_barber_sees_and_manages_only_own_appointments(self):
        other_barber_user = self.create_user(
            'outro-barbeiro@example.com', User.TipoPerfil.BARBEIRO
        )
        other_barber = Barber.objects.create(
            user=other_barber_user,
            barbershop=self.barbershop,
        )
        other_appointment = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=other_barber,
            servico=self.service,
            data_hora=self.start + timedelta(minutes=60),
        )
        self.client.force_authenticate(self.barber.user)

        list_response = self.client.get(reverse('appointment-list'))
        blocked_response = self.client.patch(
            reverse('appointment-detail', args=[other_appointment.pk]),
            {'observacoes': 'Alteração indevida'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in list_response.data['results']],
            [self.existing_appointment.pk],
        )
        self.assertEqual(blocked_response.status_code, status.HTTP_404_NOT_FOUND)

        create_response = self.client.post(
            reverse('appointment-list'),
            {
                **self.appointment_payload(self.start + timedelta(minutes=60)),
                'barbeiro': other_barber.pk,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('barbeiro', create_response.data)
