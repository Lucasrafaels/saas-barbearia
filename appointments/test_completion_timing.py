"""
BUS-07 — "realizado" só depois do término previsto do atendimento.

Critério: a transição para `realizado` é aceita quando o instante atual é
maior ou igual a `data_hora + servico.duracao`, o mesmo intervalo que a
agenda usa para conflitos e horários livres. A comparação é feita entre
instantes absolutos (datetimes aware), então o TIME_ZONE do projeto
(America/Sao_Paulo) não desloca o limite.
"""
from datetime import datetime, time, timedelta, timezone as dt_timezone
from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment

PASSWORD = 'Senha-segura-123'
# 12/03/2030, 10:00 em São Paulo (UTC-3) = 13:00 UTC.
START = timezone.make_aware(datetime(2030, 3, 12, 10, 0))
TERMINO_PREVISTO = 'término previsto'


def frozen_at(instant):
    return mock.patch('django.utils.timezone.now', return_value=instant)


class CompletionTimingTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Central', endereco='Rua Principal, 100', telefone='11999999999',
            email='central@example.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.barber = Barber.objects.create(
            user=self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO), barbershop=self.shop,
        )
        self.service = Service.objects.create(barbershop=self.shop, nome='Corte', preco='50.00', duracao=30)
        self.appointment = self.create_appointment(START, Appointment.Status.CONFIRMADO)
        self.client.force_authenticate(self.admin)

    def create_user(self, email, perfil):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=self.shop,
        )

    def create_appointment(self, data_hora, status_, service=None):
        return Appointment.objects.create(
            barbershop=self.shop, cliente=self.client_user, barbeiro=self.barber,
            servico=service or self.service, data_hora=data_hora, status=status_,
            preco_historico='50.00',
        )

    def complete(self, appointment, now=None):
        url = reverse('appointment-detail', args=[appointment.pk])
        if now is None:
            return self.client.patch(url, {'status': 'realizado'}, format='json')
        with frozen_at(now):
            return self.client.patch(url, {'status': 'realizado'}, format='json')

    def assert_rejected(self, response, appointment, expected_status=Appointment.Status.CONFIRMADO, text=TERMINO_PREVISTO):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(text, str(response.data['status']))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, expected_status)

    # Agendamento futuro -------------------------------------------------------

    def test_nao_conclui_agendamento_futuro(self):
        self.assert_rejected(self.complete(self.appointment, now=START - timedelta(days=1)), self.appointment)

    def test_nao_conclui_agendamento_futuro_no_relogio_real(self):
        amanha = timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), time(10)))
        futuro = self.create_appointment(amanha, Appointment.Status.CONFIRMADO)

        self.assert_rejected(self.complete(futuro), futuro)

    def test_criacao_direta_como_realizado_e_recusada(self):
        amanha = timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), time(11)))
        before = Appointment.objects.count()

        response = self.client.post(reverse('appointment-list'), {
            'cliente': self.client_user.pk, 'barbeiro': self.barber.pk, 'servico': self.service.pk,
            'data_hora': amanha.isoformat(), 'status': 'realizado',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(TERMINO_PREVISTO, str(response.data['status']))
        self.assertEqual(Appointment.objects.count(), before)

    # Antes do término previsto ----------------------------------------------

    def test_nao_conclui_no_inicio_nem_durante_o_atendimento(self):
        for now in (START, START + timedelta(minutes=15), START + timedelta(minutes=29, seconds=59)):
            self.assert_rejected(self.complete(self.appointment, now=now), self.appointment)

    def test_termino_considera_a_duracao_do_servico(self):
        longo = Service.objects.create(barbershop=self.shop, nome='Corte e barba', preco='80.00', duracao=60)
        appointment = self.create_appointment(START + timedelta(hours=2), Appointment.Status.CONFIRMADO, longo)

        self.assert_rejected(self.complete(appointment, now=START + timedelta(hours=2, minutes=45)), appointment)
        response = self.complete(appointment, now=START + timedelta(hours=3))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    # Momento permitido ---------------------------------------------------------

    def test_conclui_exatamente_no_termino_previsto(self):
        response = self.complete(self.appointment, now=START + timedelta(minutes=30))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.REALIZADO)
        self.assertEqual(str(self.appointment.preco_historico), '50.00')

    def test_barbeiro_conclui_depois_do_termino(self):
        self.client.force_authenticate(self.barber.user)

        response = self.complete(self.appointment, now=START + timedelta(days=1))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    # Estados incompatíveis ------------------------------------------------------

    def test_cancelado_nao_pode_ser_concluido(self):
        cancelado = self.create_appointment(START + timedelta(hours=2), Appointment.Status.CANCELADO)

        response = self.complete(cancelado, now=START + timedelta(days=1))

        self.assert_rejected(response, cancelado, Appointment.Status.CANCELADO, text='cancelado')

    def test_agendado_nao_pula_direto_para_realizado(self):
        agendado = self.create_appointment(START + timedelta(hours=2), Appointment.Status.AGENDADO)

        response = self.complete(agendado, now=START + timedelta(days=1))

        self.assert_rejected(response, agendado, Appointment.Status.AGENDADO, text='Transição inválida')

    def test_realizado_continua_estado_final(self):
        with frozen_at(START + timedelta(days=1)):
            self.complete(self.appointment)
            response = self.client.patch(
                reverse('appointment-detail', args=[self.appointment.pk]), {'status': 'cancelado'}, format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.REALIZADO)

    # Fuso horário ---------------------------------------------------------------

    def test_limite_e_um_instante_absoluto_e_nao_um_horario_de_parede(self):
        self.assertEqual(settings.TIME_ZONE, 'America/Sao_Paulo')
        self.assertTrue(settings.USE_TZ)
        # 10:00 em São Paulo é 13:00 UTC; o término previsto é 13:30 UTC.
        self.assertEqual(START.astimezone(dt_timezone.utc), datetime(2030, 3, 12, 13, 0, tzinfo=dt_timezone.utc))

        # 13:15 UTC (10:15 local): no relógio de parede UTC já passou das 10:30,
        # mas o atendimento ainda está em andamento.
        response = self.complete(self.appointment, now=datetime(2030, 3, 12, 13, 15, tzinfo=dt_timezone.utc))
        self.assert_rejected(response, self.appointment)
        # A mensagem mostra o término no horário local da barbearia.
        self.assertIn('12/03/2030 às 10:30', str(response.data['status']))

        response = self.complete(self.appointment, now=datetime(2030, 3, 12, 13, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_fluxo_completo_pela_api_com_horario_em_utc(self):
        self.client.force_authenticate(self.barber.user)
        url_list = reverse('appointment-list')

        with frozen_at(datetime(2030, 3, 13, 11, 0, tzinfo=dt_timezone.utc)):  # 08:00 local
            created = self.client.post(url_list, {
                'cliente': self.client_user.pk, 'barbeiro': self.barber.pk, 'servico': self.service.pk,
                'data_hora': '2030-03-13T13:00:00Z',  # 10:00 local
            }, format='json')
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
            appointment = Appointment.objects.get(pk=created.data['id'])
            confirm = self.client.patch(
                reverse('appointment-detail', args=[appointment.pk]), {'status': 'confirmado'}, format='json',
            )
            self.assertEqual(confirm.status_code, status.HTTP_200_OK, confirm.data)

        self.assert_rejected(
            self.complete(appointment, now=datetime(2030, 3, 13, 13, 29, tzinfo=dt_timezone.utc)), appointment,
        )
        response = self.complete(appointment, now=datetime(2030, 3, 13, 13, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    # Fora da API ----------------------------------------------------------------

    def test_modelo_recusa_conclusao_antecipada_fora_da_api(self):
        self.appointment.status = Appointment.Status.REALIZADO

        with frozen_at(START + timedelta(minutes=10)), self.assertRaises(ValidationError) as ctx:
            self.appointment.full_clean()
        self.assertIn('status', ctx.exception.message_dict)

        with frozen_at(START + timedelta(minutes=30)):
            self.appointment.full_clean()
