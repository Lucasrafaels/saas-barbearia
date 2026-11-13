"""
BUS-06 — agendamentos respeitam os dias de funcionamento de cada barbearia.

`Barbershop.dias_funcionamento` guarda os dias da semana (ISO: 1 = segunda
... 7 = domingo). O padrão são todos os dias, para não fechar domingos de
barbearias que já os atendem. Dia fechado não tem horários livres e não
aceita agendamento nem remarcação, por nenhum perfil.
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
SEGUNDA_A_SABADO = [1, 2, 3, 4, 5, 6]


def proximo(dia_iso, minimo=2):
    """Próxima data (a partir de hoje + `minimo`) cujo dia da semana ISO é `dia_iso`."""
    data = timezone.localdate() + timedelta(days=minimo)
    while data.isoweekday() != dia_iso:
        data += timedelta(days=1)
    return data


def local(data, hora, minuto=0):
    return timezone.make_aware(datetime.combine(data, time(hora, minuto)))


class DiasDeFuncionamentoTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Dias', endereco='Rua C, 3', telefone='11999999999',
            email='dias@example.com', horario_abertura=time(9), horario_fechamento=time(19),
        )
        self.admin = self.user('admin@example.com', User.TipoPerfil.ADMIN)
        self.cliente = self.user('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.barbeiro_user = self.user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barbeiro = Barber.objects.create(user=self.barbeiro_user, barbershop=self.shop)
        self.servico = Service.objects.create(barbershop=self.shop, nome='Corte', preco='45.00', duracao=30)
        self.domingo = proximo(7)
        self.sabado = proximo(6)
        self.segunda = proximo(1)

    def user(self, email, perfil, shop=None):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=shop or self.shop,
        )

    def fechar_domingos(self):
        Barbershop.objects.filter(pk=self.shop.pk).update(dias_funcionamento=SEGUNDA_A_SABADO)

    def agendar(self, quem, quando):
        self.client.force_authenticate(quem)
        return self.client.post(reverse('appointment-list'), {
            'cliente': self.cliente.pk, 'barbeiro': self.barbeiro.pk, 'servico': self.servico.pk,
            'data_hora': quando.isoformat(),
        }, format='json')

    def horarios(self, quem, data):
        self.client.force_authenticate(quem)
        return self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': self.barbeiro.pk, 'servico': self.servico.pk, 'data': data.isoformat(),
        })

    def editar_barbearia(self, quem, payload):
        self.client.force_authenticate(quem)
        return self.client.patch(reverse('barbershop-detail', args=[self.shop.pk]), payload, format='json')

    # Configuração ------------------------------------------------------------

    def test_padrao_sao_todos_os_dias(self):
        self.assertEqual(self.shop.dias_funcionamento, [1, 2, 3, 4, 5, 6, 7])
        self.client.force_authenticate(self.cliente)
        response = self.client.get(reverse('barbershop-detail', args=[self.shop.pk]))
        self.assertEqual(response.data['dias_funcionamento'], [1, 2, 3, 4, 5, 6, 7])

    def test_onboarding_sem_dias_usa_o_padrao(self):
        novo = User.objects.create_user(email='dono@example.com', nome='Dono', password=PASSWORD)
        self.client.force_authenticate(novo)

        response = self.client.post(reverse('barbershop-list'), {
            'nome': 'Nova', 'endereco': 'Rua D, 4', 'telefone': '11988887777', 'email': 'nova@example.com',
            'horario_abertura': '09:00:00', 'horario_fechamento': '18:00:00',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['dias_funcionamento'], [1, 2, 3, 4, 5, 6, 7])

    def test_admin_configura_os_dias_e_a_api_normaliza(self):
        response = self.editar_barbearia(self.admin, {'dias_funcionamento': [6, 1, 2, 3, 4, 5, 1]})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['dias_funcionamento'], SEGUNDA_A_SABADO)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.dias_funcionamento, SEGUNDA_A_SABADO)

    def test_dias_invalidos_sao_recusados(self):
        for invalido in ([], [0], [8], [True], 'segunda', None, [1.5]):
            with self.subTest(valor=invalido):
                response = self.editar_barbearia(self.admin, {'dias_funcionamento': invalido})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                self.assertIn('dias_funcionamento', response.data)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.dias_funcionamento, [1, 2, 3, 4, 5, 6, 7])

    def test_cliente_e_barbeiro_nao_alteram_os_dias(self):
        for quem in (self.cliente, self.barbeiro_user):
            with self.subTest(perfil=quem.tipo_perfil):
                response = self.editar_barbearia(quem, {'dias_funcionamento': [7]})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.dias_funcionamento, [1, 2, 3, 4, 5, 6, 7])

    def test_modelo_recusa_dias_invalidos_fora_da_api(self):
        # Ex.: JSON digitado no Django Admin.
        for invalido in ([], 'segunda', {'dia': 1}, [0], [8], [True], ['1']):
            with self.subTest(valor=invalido):
                self.shop.dias_funcionamento = invalido
                with self.assertRaises(ValidationError) as contexto:
                    self.shop.full_clean()
                self.assertIn('dias_funcionamento', contexto.exception.message_dict)

    def test_modelo_normaliza_dias_validos(self):
        self.shop.dias_funcionamento = [7, 1, 1, 3]
        self.shop.full_clean()
        self.assertEqual(self.shop.dias_funcionamento, [1, 3, 7])

    # Agendamento em dia fechado ------------------------------------------------

    def test_nenhum_perfil_agenda_em_dia_fechado(self):
        self.fechar_domingos()
        for quem in (self.cliente, self.admin, self.barbeiro_user):
            with self.subTest(perfil=quem.tipo_perfil):
                response = self.agendar(quem, local(self.domingo, 10))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                self.assertIn('aos domingos', str(response.data['data_hora']))
        self.assertEqual(Appointment.objects.count(), 0)

    def test_dia_fechado_nao_tem_horarios_livres(self):
        self.fechar_domingos()

        fechado = self.horarios(self.cliente, self.domingo)
        aberto = self.horarios(self.cliente, self.sabado)

        self.assertEqual(fechado.status_code, status.HTTP_200_OK)
        self.assertEqual(fechado.data['slots'], [])
        self.assertIn('09:00', aberto.data['slots'])

    def test_domingo_aberto_continua_aceitando_agendamentos(self):
        # Não há bloqueio fixo de domingo: vale a configuração de cada barbearia.
        self.assertIn('10:00', self.horarios(self.cliente, self.domingo).data['slots'])

        response = self.agendar(self.cliente, local(self.domingo, 10))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_barbearia_que_fecha_na_segunda_e_abre_no_domingo(self):
        Barbershop.objects.filter(pk=self.shop.pk).update(dias_funcionamento=[2, 3, 4, 5, 6, 7])

        segunda = self.agendar(self.cliente, local(self.segunda, 10))
        domingo = self.agendar(self.cliente, local(self.domingo, 10))

        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST, segunda.data)
        self.assertIn('às segundas-feiras', str(segunda.data['data_hora']))
        self.assertEqual(domingo.status_code, status.HTTP_201_CREATED, domingo.data)

    def test_remarcacao_para_dia_fechado_e_recusada(self):
        agendamento = Appointment.objects.create(
            barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=self.servico,
            data_hora=local(self.sabado, 10), preco_historico='45.00',
        )
        self.fechar_domingos()
        self.client.force_authenticate(self.cliente)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'data_hora': local(self.domingo, 10).isoformat()}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.data_hora, local(self.sabado, 10))

    def test_horario_ja_marcado_num_dia_que_depois_fechou_continua_gerenciavel(self):
        # Fechar um dia não trava os horários que já existiam nele.
        agendamento = Appointment.objects.create(
            barbershop=self.shop, cliente=self.cliente, barbeiro=self.barbeiro, servico=self.servico,
            data_hora=local(self.domingo, 10), preco_historico='45.00',
        )
        self.fechar_domingos()
        self.client.force_authenticate(self.admin)
        url = reverse('appointment-detail', args=[agendamento.pk])

        observacao = self.client.patch(url, {'observacoes': 'Avisar o cliente.'}, format='json')
        confirmacao = self.client.patch(url, {'status': 'confirmado'}, format='json')
        cancelamento = self.client.delete(url)

        self.assertEqual(observacao.status_code, status.HTTP_200_OK, observacao.data)
        self.assertEqual(confirmacao.status_code, status.HTTP_200_OK, confirmacao.data)
        self.assertEqual(cancelamento.status_code, status.HTTP_204_NO_CONTENT)

    def test_regra_vale_fora_da_api(self):
        self.fechar_domingos()
        agendamento = Appointment(
            barbershop=Barbershop.objects.get(pk=self.shop.pk), cliente=self.cliente, barbeiro=self.barbeiro,
            servico=self.servico, data_hora=local(self.domingo, 10), preco_historico='45.00',
        )
        with self.assertRaises(ValidationError) as contexto:
            agendamento.full_clean()
        self.assertIn('data_hora', contexto.exception.message_dict)

    # Fuso horário: o dia da semana é o do horário local da barbearia --------------

    def test_dia_da_semana_e_o_local_e_nao_o_utc(self):
        Barbershop.objects.filter(pk=self.shop.pk).update(
            dias_funcionamento=SEGUNDA_A_SABADO, horario_fechamento=time(23),
        )
        sabado_22h = local(self.sabado, 22)       # domingo 01:00 em UTC
        domingo_9h = local(self.domingo, 9)       # domingo 12:00 em UTC
        self.assertEqual(sabado_22h.astimezone(dt_timezone.utc).isoweekday(), 7)

        aceito = self.agendar(self.cliente, sabado_22h.astimezone(dt_timezone.utc))
        recusado = self.agendar(self.cliente, domingo_9h.astimezone(dt_timezone.utc))

        self.assertEqual(aceito.status_code, status.HTTP_201_CREATED, aceito.data)
        self.assertEqual(recusado.status_code, status.HTTP_400_BAD_REQUEST, recusado.data)

    # Isolamento ------------------------------------------------------------------

    def test_configuracao_de_uma_barbearia_nao_afeta_outra(self):
        outra = Barbershop.objects.create(
            nome='Outra', endereco='Rua E, 5', telefone='11977776666', email='outra@example.com',
            horario_abertura=time(9), horario_fechamento=time(19), dias_funcionamento=[1, 2, 3, 4, 5],
        )
        self.assertEqual(outra.dias_funcionamento, [1, 2, 3, 4, 5])

        response = self.agendar(self.cliente, local(self.domingo, 10))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
