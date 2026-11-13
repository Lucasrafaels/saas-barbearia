"""
BUS-15 — o status inicial de um agendamento é definido pelo backend.

O cliente cria horários "agendado", que aguardam a confirmação da barbearia.
Mandar `status` direto na requisição (JSON ou formulário) não contorna essa
aprovação. Admin e barbeiro, que representam a barbearia, continuam podendo
registrar um horário já confirmado (ex.: agendamento por telefone). Nenhum
perfil cria um registro novo como cancelado ou realizado.
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
    """Horário local daqui a `dias` dias (sempre no futuro nos testes)."""
    return timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=dias), time(hora, minuto)))


class StatusInicialTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Status', endereco='Rua A, 1', telefone='11999999999',
            email='status@example.com', horario_abertura=time(9), horario_fechamento=time(19),
        )
        self.admin = self.user('admin@example.com', User.TipoPerfil.ADMIN)
        self.cliente = self.user('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.outro_cliente = self.user('outro@example.com', User.TipoPerfil.CLIENTE)
        self.barbeiro_user = self.user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barbeiro = Barber.objects.create(user=self.barbeiro_user, barbershop=self.shop)
        self.servico = Service.objects.create(barbershop=self.shop, nome='Corte', preco='45.00', duracao=30)

    def user(self, email, perfil):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=self.shop,
        )

    def payload(self, cliente=None, quando=None, **extra):
        return {
            'cliente': (cliente or self.cliente).pk,
            'barbeiro': self.barbeiro.pk,
            'servico': self.servico.pk,
            'data_hora': (quando or em(3, 10)).isoformat(),
            **extra,
        }

    def criar(self, quem, fmt='json', **payload):
        self.client.force_authenticate(quem)
        return self.client.post(reverse('appointment-list'), self.payload(**payload), format=fmt)

    # Cliente tentando contornar a aprovação -----------------------------------

    def test_cliente_nao_cria_agendamento_ja_confirmado(self):
        response = self.criar(self.cliente, status='confirmado')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_cliente_nao_cria_agendamento_com_status_final(self):
        for status_final in ('cancelado', 'realizado'):
            with self.subTest(status=status_final):
                response = self.criar(self.cliente, status=status_final)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_status_enviado_como_formulario_tambem_e_recusado(self):
        response = self.criar(self.cliente, fmt='multipart', status='confirmado')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_cliente_nao_contorna_combinando_status_e_outro_cliente(self):
        response = self.criar(self.cliente, cliente=self.outro_cliente, status='confirmado')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_status_invalido_nao_vira_erro_500(self):
        response = self.criar(self.cliente, status='aprovado')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    # Fluxo legítimo do cliente --------------------------------------------------

    def test_cliente_sem_status_cria_agendado(self):
        response = self.criar(self.cliente)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.AGENDADO)
        self.assertEqual(Appointment.objects.get().status, Appointment.Status.AGENDADO)

    def test_cliente_enviando_agendado_explicitamente_e_aceito(self):
        response = self.criar(self.cliente, status='agendado')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.AGENDADO)

    def test_horario_do_cliente_entra_na_fila_a_confirmar_da_barbearia(self):
        self.criar(self.cliente)
        self.client.force_authenticate(self.admin)

        response = self.client.get(reverse('appointment-list'), {'status': 'agendado'})

        self.assertEqual(response.data['count'], 1)
        confirmacao = self.client.patch(
            reverse('appointment-detail', args=[response.data['results'][0]['id']]),
            {'status': 'confirmado'}, format='json',
        )
        self.assertEqual(confirmacao.status_code, status.HTTP_200_OK, confirmacao.data)
        self.assertEqual(confirmacao.data['status'], Appointment.Status.CONFIRMADO)

    # Lado da barbearia: fluxos legítimos preservados ------------------------------

    def test_admin_sem_status_cria_agendado(self):
        response = self.criar(self.admin)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.AGENDADO)

    def test_admin_registra_horario_ja_confirmado(self):
        response = self.criar(self.admin, status='confirmado')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.CONFIRMADO)

    def test_barbeiro_registra_horario_ja_confirmado_na_propria_agenda(self):
        response = self.criar(self.barbeiro_user, status='confirmado')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], Appointment.Status.CONFIRMADO)
        self.assertEqual(response.data['barbeiro'], self.barbeiro.pk)

    def test_ninguem_cria_agendamento_ja_cancelado(self):
        for quem in (self.admin, self.barbeiro_user):
            with self.subTest(perfil=quem.tipo_perfil):
                response = self.criar(quem, status='cancelado')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                self.assertIn('status', response.data)
        self.assertEqual(Appointment.objects.count(), 0)

    # Regra também fora da API (Django Admin, shell) -----------------------------

    def test_modelo_recusa_registro_novo_cancelado(self):
        agendamento = Appointment(
            barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=self.servico,
            data_hora=em(3, 11), status=Appointment.Status.CANCELADO, preco_historico='45.00',
        )
        with self.assertRaises(ValidationError) as contexto:
            agendamento.full_clean()
        self.assertIn('status', contexto.exception.message_dict)

    def test_modelo_aceita_registro_novo_agendado_ou_confirmado(self):
        for hora, status_inicial in ((11, Appointment.Status.AGENDADO), (12, Appointment.Status.CONFIRMADO)):
            with self.subTest(status=status_inicial):
                Appointment(
                    barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=self.servico,
                    data_hora=em(3, hora), status=status_inicial, preco_historico='45.00',
                ).full_clean()
