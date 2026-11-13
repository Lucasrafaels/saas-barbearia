"""
BUS-03 — remarcação pelo cliente volta a aguardar a confirmação da barbearia.

A barbearia confirmou o horário antigo, não o novo. Quando o cliente muda o
horário, o barbeiro ou o serviço de um agendamento confirmado, ele volta a
"agendado". Alterações feitas pelo lado da barbearia (admin e barbeiro)
mantêm o status, como antes. Editar só as observações não muda nada.
"""
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service

PASSWORD = 'Senha-segura-123'


def em(dias, hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=dias), time(hora, minuto)))


class RemarcacaoStatusTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Remarcação', endereco='Rua B, 2', telefone='11999999999',
            email='remarcacao@example.com', horario_abertura=time(9), horario_fechamento=time(19),
        )
        self.admin = self.user('admin@example.com', User.TipoPerfil.ADMIN)
        self.cliente = self.user('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.barbeiro_user = self.user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barbeiro = Barber.objects.create(user=self.barbeiro_user, barbershop=self.shop)
        self.outro_barbeiro = Barber.objects.create(
            user=self.user('outro.barbeiro@example.com', User.TipoPerfil.BARBEIRO), barbershop=self.shop,
        )
        self.corte = Service.objects.create(barbershop=self.shop, nome='Corte', preco='45.00', duracao=30)
        self.barba = Service.objects.create(barbershop=self.shop, nome='Barba', preco='35.00', duracao=30)
        self.agendamento = self.criar(Appointment.Status.CONFIRMADO)

    def user(self, email, perfil):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=self.shop,
        )

    def criar(self, status_, quando=None):
        return Appointment.objects.create(
            barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=self.corte,
            data_hora=quando or em(3, 10), status=status_, preco_historico='45.00',
        )

    def patch(self, quem, payload, agendamento=None):
        self.client.force_authenticate(quem)
        return self.client.patch(
            reverse('appointment-detail', args=[(agendamento or self.agendamento).pk]), payload, format='json',
        )

    def assert_status(self, response, esperado):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], esperado)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, esperado)

    # Cliente remarcando um horário confirmado ----------------------------------

    def test_cliente_muda_o_horario_e_volta_a_agendado(self):
        response = self.patch(self.cliente, {'data_hora': em(3, 11).isoformat()})

        self.assert_status(response, Appointment.Status.AGENDADO)
        self.assertEqual(self.agendamento.data_hora, em(3, 11))

    def test_cliente_muda_o_barbeiro_e_volta_a_agendado(self):
        response = self.patch(self.cliente, {'barbeiro': self.outro_barbeiro.pk})

        self.assert_status(response, Appointment.Status.AGENDADO)

    def test_cliente_muda_o_servico_e_volta_a_agendado(self):
        response = self.patch(self.cliente, {'servico': self.barba.pk})

        self.assert_status(response, Appointment.Status.AGENDADO)

    def test_cliente_nao_mantem_confirmado_mandando_o_status_junto(self):
        response = self.patch(self.cliente, {'data_hora': em(3, 11).isoformat(), 'status': 'confirmado'})

        self.assert_status(response, Appointment.Status.AGENDADO)

    def test_cliente_nao_muda_o_status_junto_com_a_remarcacao(self):
        response = self.patch(self.cliente, {'data_hora': em(3, 11).isoformat(), 'status': 'realizado'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Appointment.Status.CONFIRMADO)
        self.assertEqual(self.agendamento.data_hora, em(3, 10))

    def test_remarcacao_preserva_o_preco_historico(self):
        self.patch(self.cliente, {'data_hora': em(4, 15).isoformat()})

        self.agendamento.refresh_from_db()
        self.assertEqual(str(self.agendamento.preco_historico), '45.00')

    def test_barbearia_confirma_de_novo_depois_da_remarcacao(self):
        self.patch(self.cliente, {'data_hora': em(3, 11).isoformat()})

        response = self.patch(self.admin, {'status': 'confirmado'})

        self.assert_status(response, Appointment.Status.CONFIRMADO)

    # Alterações que não exigem nova aprovação ----------------------------------

    def test_cliente_editando_so_observacoes_mantem_confirmado(self):
        response = self.patch(self.cliente, {'observacoes': 'Chego cinco minutos antes.'})

        self.assert_status(response, Appointment.Status.CONFIRMADO)

    def test_reenviar_os_mesmos_dados_mantem_confirmado(self):
        response = self.patch(self.cliente, {
            'data_hora': em(3, 10).isoformat(), 'barbeiro': self.barbeiro.pk, 'servico': self.corte.pk,
        })

        self.assert_status(response, Appointment.Status.CONFIRMADO)

    def test_remarcar_um_horario_ainda_agendado_continua_agendado(self):
        pendente = self.criar(Appointment.Status.AGENDADO, quando=em(4, 10))

        response = self.patch(self.cliente, {'data_hora': em(4, 11).isoformat()}, agendamento=pendente)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.AGENDADO)

    # Lado da barbearia: comportamento mantido ---------------------------------

    def test_admin_remarcando_mantem_confirmado(self):
        response = self.patch(self.admin, {'data_hora': em(3, 11).isoformat()})

        self.assert_status(response, Appointment.Status.CONFIRMADO)

    def test_barbeiro_remarcando_a_propria_agenda_mantem_confirmado(self):
        response = self.patch(self.barbeiro_user, {'data_hora': em(3, 11).isoformat()})

        self.assert_status(response, Appointment.Status.CONFIRMADO)

    def test_reabrir_sem_remarcar_continua_proibido(self):
        response = self.patch(self.admin, {'status': 'agendado'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Appointment.Status.CONFIRMADO)

    # Máquina de estados no modelo ----------------------------------------------

    def test_modelo_so_aceita_confirmado_para_agendado_numa_remarcacao(self):
        self.agendamento.status = Appointment.Status.AGENDADO
        with self.assertRaises(ValidationError):
            self.agendamento.full_clean()

        self.agendamento.data_hora = em(3, 12)
        self.agendamento.full_clean()
