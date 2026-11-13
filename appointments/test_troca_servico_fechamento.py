"""
BUS-04 — trocar o serviço revalida o horário de término.

O término é `data_hora + duração do serviço` e não pode passar do fechamento.
Antes, a validação só rodava quando `data_hora` mudava: trocar um serviço de
30 min por um de 60 min às 18:30, com fechamento às 19:00, era aceito.
Terminar exatamente no fechamento continua permitido.
"""
from datetime import datetime, time, timedelta, timezone as dt_timezone

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


class TrocaDeServicoTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Serviços', endereco='Rua H, 8', telefone='11999999999',
            email='servicos@example.com', horario_abertura=time(9), horario_fechamento=time(19),
        )
        self.admin = self.user('admin@example.com', User.TipoPerfil.ADMIN)
        self.cliente = self.user('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.barbeiro_user = self.user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barbeiro = Barber.objects.create(user=self.barbeiro_user, barbershop=self.shop)
        self.corte = Service.objects.create(barbershop=self.shop, nome='Corte', preco='45.00', duracao=30)
        self.barba = Service.objects.create(barbershop=self.shop, nome='Barba', preco='35.00', duracao=30)
        self.combo = Service.objects.create(barbershop=self.shop, nome='Corte + Barba', preco='70.00', duracao=60)

    def user(self, email, perfil):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=self.shop,
        )

    def criar(self, quando, servico=None, status_=Appointment.Status.AGENDADO):
        servico = servico or self.corte
        return Appointment.objects.create(
            barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=servico,
            data_hora=quando, status=status_, preco_historico=servico.preco,
        )

    def patch(self, quem, agendamento, payload):
        self.client.force_authenticate(quem)
        return self.client.patch(reverse('appointment-detail', args=[agendamento.pk]), payload, format='json')

    def assert_recusado(self, response, agendamento, servico_original):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('fechamento', str(response.data['data_hora']))
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.servico_id, servico_original.pk)
        self.assertEqual(str(agendamento.preco_historico), servico_original.preco)

    # Cenário da auditoria, pelos três perfis -------------------------------------

    def test_admin_troca_por_servico_que_passa_do_fechamento(self):
        agendamento = self.criar(em(3, 18, 30))

        self.assert_recusado(self.patch(self.admin, agendamento, {'servico': self.combo.pk}), agendamento, self.corte)

    def test_cliente_troca_por_servico_que_passa_do_fechamento(self):
        agendamento = self.criar(em(3, 18, 30))

        self.assert_recusado(self.patch(self.cliente, agendamento, {'servico': self.combo.pk}), agendamento, self.corte)

    def test_barbeiro_troca_por_servico_que_passa_do_fechamento(self):
        agendamento = self.criar(em(3, 18, 30))

        self.assert_recusado(
            self.patch(self.barbeiro_user, agendamento, {'servico': self.combo.pk}), agendamento, self.corte,
        )

    def test_horario_fora_da_grade_tambem_e_revalidado(self):
        agendamento = self.criar(em(3, 18, 15))

        self.assert_recusado(self.patch(self.admin, agendamento, {'servico': self.combo.pk}), agendamento, self.corte)

    # Limites ---------------------------------------------------------------------

    def test_terminar_exatamente_no_fechamento_e_permitido(self):
        agendamento = self.criar(em(3, 18, 0))

        response = self.patch(self.admin, agendamento, {'servico': self.combo.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.servico_id, self.combo.pk)
        self.assertEqual(str(agendamento.preco_historico), '70.00')

    def test_troca_por_servico_de_mesma_duracao_no_fim_do_dia_e_permitida(self):
        agendamento = self.criar(em(3, 18, 30))

        response = self.patch(self.cliente, agendamento, {'servico': self.barba.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_trocar_servico_e_antecipar_o_horario_juntos_e_permitido(self):
        agendamento = self.criar(em(3, 18, 30))

        response = self.patch(self.cliente, agendamento, {'servico': self.combo.pk, 'data_hora': em(3, 17).isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_limite_considera_o_fuso_local_com_horario_em_utc(self):
        agendamento = self.criar(em(3, 17, 30))
        # 18:30 locais enviados em UTC: o combo terminaria às 19:30 locais.
        response = self.patch(self.cliente, agendamento, {
            'servico': self.combo.pk, 'data_hora': em(3, 18, 30).astimezone(dt_timezone.utc).isoformat(),
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('fechamento', str(response.data['data_hora']))

    # Fluxos que não mexem no serviço continuam como antes -------------------------

    def test_mudar_so_o_status_nao_revalida_o_horario(self):
        agendamento = self.criar(em(3, 18, 30))
        # A duração do serviço mudou depois do agendamento (BUS-09, fora deste escopo).
        Service.objects.filter(pk=self.corte.pk).update(duracao=60)

        response = self.patch(self.admin, agendamento, {'status': 'confirmado'})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_modelo_recusa_a_troca_fora_da_api(self):
        agendamento = self.criar(em(3, 18, 30))
        agendamento.servico = self.combo

        with self.assertRaises(ValidationError) as contexto:
            agendamento.full_clean()
        self.assertIn('data_hora', contexto.exception.message_dict)
