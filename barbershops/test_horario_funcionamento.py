"""
BUS-05 — o fechamento precisa ser depois da abertura.

O projeto não opera atravessando a meia-noite: `Appointment` recusa
atendimento que termina em outro dia, e os horários livres vão da abertura
ao fechamento do mesmo dia. Por isso fechamento ≤ abertura é sempre inválido,
na criação (onboarding), na edição completa e no PATCH parcial, que compara
o campo enviado com o valor gravado.
"""
from datetime import time

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barbershop

PASSWORD = 'Senha-segura-123'


class HorarioDeFuncionamentoTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Horário', endereco='Rua F, 6', telefone='11999999999',
            email='horario@example.com', horario_abertura=time(9), horario_fechamento=time(19),
        )
        self.admin = User.objects.create_user(
            email='admin@example.com', nome='Admin', password=PASSWORD,
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=self.shop,
        )
        self.url = reverse('barbershop-detail', args=[self.shop.pk])

    def patch(self, payload):
        self.client.force_authenticate(self.admin)
        return self.client.patch(self.url, payload, format='json')

    def assert_recusado(self, response):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('fechamento precisa ser depois', str(response.data['horario_fechamento']))
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.horario_abertura, self.shop.horario_fechamento), (time(9), time(19)))

    # Edição ------------------------------------------------------------------

    def test_fechamento_antes_da_abertura_e_recusado(self):
        self.assert_recusado(self.patch({'horario_abertura': '18:00:00', 'horario_fechamento': '08:00:00'}))

    def test_fechamento_igual_a_abertura_e_recusado(self):
        self.assert_recusado(self.patch({'horario_abertura': '10:00:00', 'horario_fechamento': '10:00:00'}))

    def test_patch_parcial_so_do_fechamento_e_comparado_com_a_abertura_gravada(self):
        self.assert_recusado(self.patch({'horario_fechamento': '08:30:00'}))
        self.assert_recusado(self.patch({'horario_fechamento': '09:00:00'}))

    def test_patch_parcial_so_da_abertura_e_comparado_com_o_fechamento_gravado(self):
        self.assert_recusado(self.patch({'horario_abertura': '19:30:00'}))

    def test_horario_que_atravessa_a_meia_noite_e_recusado(self):
        self.assert_recusado(self.patch({'horario_abertura': '22:00:00', 'horario_fechamento': '02:00:00'}))
        self.assert_recusado(self.patch({'horario_fechamento': '00:00:00'}))

    def test_um_minuto_depois_da_abertura_e_aceito(self):
        response = self.patch({'horario_abertura': '09:00:00', 'horario_fechamento': '09:01:00'})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.horario_fechamento, time(9, 1))

    def test_edicao_valida_continua_funcionando(self):
        response = self.patch({'horario_abertura': '08:00:00', 'horario_fechamento': '20:30:00', 'nome': 'Novo nome'})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual((response.data['horario_abertura'], response.data['horario_fechamento']), ('08:00:00', '20:30:00'))

    def test_editar_outros_campos_nao_exige_reenviar_o_horario(self):
        response = self.patch({'telefone': '11911112222'})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    # Criação (onboarding) -------------------------------------------------------

    def test_onboarding_com_horario_invalido_nao_cria_barbearia(self):
        dono = User.objects.create_user(email='dono@example.com', nome='Dono', password=PASSWORD)
        self.client.force_authenticate(dono)
        antes = Barbershop.objects.count()

        response = self.client.post(reverse('barbershop-list'), {
            'nome': 'Nova', 'endereco': 'Rua G, 7', 'telefone': '11988887777', 'email': 'nova@example.com',
            'horario_abertura': '18:00:00', 'horario_fechamento': '08:00:00',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('horario_fechamento', response.data)
        self.assertEqual(Barbershop.objects.count(), antes)
        dono.refresh_from_db()
        self.assertIsNone(dono.barbershop_id)
        self.assertEqual(dono.tipo_perfil, User.TipoPerfil.CLIENTE)

    # Fora da API (Django Admin, shell) ----------------------------------------

    def test_modelo_recusa_fechamento_antes_da_abertura(self):
        self.shop.horario_fechamento = time(8)
        with self.assertRaises(ValidationError) as contexto:
            self.shop.full_clean()
        self.assertIn('horario_fechamento', contexto.exception.message_dict)
