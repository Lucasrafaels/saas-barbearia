"""Regressões de cancelamento e reagendamento sem perda de histórico."""
from datetime import datetime, time, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment


class CancelamentoEReagendamentoTests(APITestCase):
    def setUp(self):
        self.shop = self.create_shop('Central', 'central@example.com')
        self.other_shop = self.create_shop('Outra', 'outra@example.com')
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN, self.shop)
        self.client_user = self.create_user('cliente@example.com', User.TipoPerfil.CLIENTE, self.shop)
        self.other_client = self.create_user('outro-cliente@example.com', User.TipoPerfil.CLIENTE, self.shop)
        self.barber = self.create_barber('barbeiro@example.com', self.shop)
        self.other_barber = self.create_barber('outro-barbeiro@example.com', self.shop)
        self.inactive_barber = self.create_barber('inativo@example.com', self.shop, ativo=False)
        self.service = Service.objects.create(
            barbershop=self.shop, nome='Corte', preco='50.00', duracao=30,
        )
        self.other_service = Service.objects.create(
            barbershop=self.shop, nome='Barba', preco='35.00', duracao=30,
        )

    @staticmethod
    def create_shop(nome, email):
        return Barbershop.objects.create(
            nome=nome, endereco='Rua Principal, 100', telefone='11999999999', email=email,
            horario_abertura=time(8), horario_fechamento=time(18),
        )

    @staticmethod
    def create_user(email, role, shop):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0], password='SenhaSegura!123',
            tipo_perfil=role, barbershop=shop,
        )

    def create_barber(self, email, shop, ativo=True):
        user = self.create_user(email, User.TipoPerfil.BARBEIRO, shop)
        return Barber.objects.create(user=user, barbershop=shop, ativo=ativo)

    @staticmethod
    def at(day_offset, hour, minute=0):
        date = timezone.localdate() + timedelta(days=day_offset)
        return timezone.make_aware(datetime.combine(date, time(hour, minute)))

    def create_appointment(self, *, cliente=None, barber=None, service=None, when=None):
        return Appointment.objects.create(
            barbershop=self.shop,
            cliente=cliente or self.client_user,
            barbeiro=barber or self.barber,
            servico=service or self.service,
            data_hora=when or self.at(2, 10),
        )

    @staticmethod
    def detail(appointment):
        return reverse('appointment-detail', args=[appointment.pk])

    def slots(self, barber, service, date, **extra):
        return self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': barber.pk,
            'servico': service.pk,
            'data': date.isoformat(),
            **extra,
        })

    def test_cliente_cancela_proprio_agendamento_sem_alterar_dados(self):
        appointment = self.create_appointment(when=self.at(2, 10))
        original = (appointment.data_hora, appointment.barbeiro_id, appointment.servico_id)
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(self.detail(appointment), {'status': 'cancelado'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELADO)
        self.assertEqual((appointment.data_hora, appointment.barbeiro_id, appointment.servico_id), original)

    def test_cliente_nao_cancela_e_altera_horario_ao_mesmo_tempo(self):
        appointment = self.create_appointment()
        original = appointment.data_hora
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'status': 'cancelado', 'data_hora': self.at(2, 11).isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.AGENDADO)
        self.assertEqual(appointment.data_hora, original)

    def test_cliente_nao_cancela_e_troca_barbeiro_ao_mesmo_tempo(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'status': 'cancelado', 'barbeiro': self.other_barber.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.AGENDADO)
        self.assertEqual(appointment.barbeiro_id, self.barber.pk)

    def test_cliente_nao_altera_agendamento_de_outra_pessoa(self):
        appointment = self.create_appointment(cliente=self.other_client)
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(self.detail(appointment), {'data_hora': self.at(2, 11).isoformat()}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        appointment.refresh_from_db()
        self.assertEqual(appointment.data_hora, self.at(2, 10))

    def test_reagendamento_com_mesmo_barbeiro_atualiza_o_mesmo_registro(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'data_hora': self.at(2, 11).isoformat(), 'barbeiro': self.barber.pk, 'servico': self.service.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Appointment.objects.count(), 1)
        appointment.refresh_from_db()
        self.assertEqual(appointment.data_hora, self.at(2, 11))

    def test_reagendamento_para_outro_barbeiro_atualiza_o_mesmo_registro(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'data_hora': self.at(2, 11).isoformat(), 'barbeiro': self.other_barber.pk, 'servico': self.service.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Appointment.objects.count(), 1)
        appointment.refresh_from_db()
        self.assertEqual(appointment.barbeiro_id, self.other_barber.pk)

    def test_disponibilidade_exclui_o_proprio_agendamento_no_mesmo_barbeiro(self):
        appointment = self.create_appointment(when=self.at(2, 10))
        self.client.force_authenticate(self.client_user)

        response = self.slots(
            self.barber, self.service, self.at(2, 10).date(), exclude_appointment_id=appointment.pk,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('10:00', response.data['slots'])

    def test_disponibilidade_para_outro_barbeiro_nao_exclui_reserva_dele(self):
        original = self.create_appointment(barber=self.barber, when=self.at(2, 10))
        self.create_appointment(cliente=self.other_client, barber=self.other_barber, when=self.at(2, 10))
        self.client.force_authenticate(self.client_user)

        response = self.slots(
            self.other_barber, self.service, self.at(2, 10).date(), exclude_appointment_id=original.pk,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('10:00', response.data['slots'])

    def test_reagendamento_para_barbeiro_inativo_e_rejeitado(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'data_hora': self.at(2, 11).isoformat(), 'barbeiro': self.inactive_barber.pk, 'servico': self.service.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertEqual(appointment.barbeiro_id, self.barber.pk)

    def test_conflito_e_revalidado_no_momento_do_patch(self):
        appointment = self.create_appointment(when=self.at(2, 10))
        self.create_appointment(cliente=self.other_client, when=self.at(2, 11))
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            self.detail(appointment),
            {'data_hora': self.at(2, 11).isoformat(), 'barbeiro': self.barber.pk, 'servico': self.service.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertEqual(appointment.data_hora, self.at(2, 10))

    def test_disponibilidade_respeita_isolamento_de_barbearia(self):
        outsider = self.create_barber('barbeiro-outra@example.com', self.other_shop)
        outsider_service = Service.objects.create(
            barbershop=self.other_shop, nome='Corte externo', preco='50.00', duracao=30,
        )
        self.client.force_authenticate(self.client_user)

        response = self.slots(outsider, outsider_service, self.at(2, 10).date())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
