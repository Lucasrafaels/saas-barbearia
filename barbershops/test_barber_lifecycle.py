"""Regressões do ciclo de vida atômico dos barbeiros."""
from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from accounts.models import User
from accounts.serializers import UserCreateSerializer
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service


class BarberLifecycleTests(APITestCase):
    def setUp(self):
        self.shop = self.create_shop('Central', 'central@example.com')
        self.other_shop = self.create_shop('Norte', 'norte@example.com')
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN, self.shop)
        self.client_user = self.create_user('cliente@example.com', User.TipoPerfil.CLIENTE, self.shop)
        self.service = Service.objects.create(
            barbershop=self.shop, nome='Corte', descricao='Corte social', preco='50.00', duracao=30,
        )

    @staticmethod
    def create_shop(nome, email):
        return Barbershop.objects.create(
            nome=nome, endereco='Rua Principal, 100', telefone='11999999999', email=email,
            horario_abertura='08:00', horario_fechamento='18:00',
        )

    @staticmethod
    def create_user(email, perfil, shop):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0], password='SenhaSegura!123',
            tipo_perfil=perfil, barbershop=shop,
        )

    @staticmethod
    def barber_payload(email='novo.barbeiro@example.com'):
        return {
            'email': email,
            'nome': 'Novo Barbeiro',
            'password': 'SenhaSegura!123',
            'tipo_perfil': User.TipoPerfil.BARBEIRO,
            'especialidade': 'Corte e barba',
        }

    def create_active_barber(self):
        user = self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO, self.shop)
        barber = Barber.objects.create(user=user, barbershop=self.shop, especialidade='Corte')
        return user, barber

    def test_cadastro_de_barbeiro_cria_usuario_e_perfil_na_mesma_chamada(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(reverse('user-list'), self.barber_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='novo.barbeiro@example.com')
        barber = Barber.objects.get(user=user)
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.BARBEIRO)
        self.assertTrue(barber.ativo)
        self.assertEqual(barber.barbershop_id, self.shop.pk)

    def test_falha_ao_criar_perfil_faz_rollback_do_usuario(self):
        request = APIRequestFactory().post(reverse('user-list'), {})
        request.user = self.admin
        serializer = UserCreateSerializer(data=self.barber_payload('rollback@example.com'), context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch.object(Barber, 'save', side_effect=IntegrityError('falha simulada')):
            with self.assertRaises(IntegrityError):
                serializer.save()

        self.assertFalse(User.objects.filter(email='rollback@example.com').exists())

    def test_administrador_nao_pode_ser_convertido_em_barbeiro(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse('barber-list'), {'user': self.admin.pk, 'especialidade': 'Corte'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Barber.objects.filter(user=self.admin).exists())

    def test_patch_desativar_sincroniza_perfil_e_preserva_agendamento(self):
        user, barber = self.create_active_barber()
        appointment = Appointment.objects.create(
            barbershop=self.shop, cliente=self.client_user, barbeiro=barber, servico=self.service,
            data_hora=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse('barber-detail', args=[barber.pk]), {'ativo': False}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        barber.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(barber.ativo)
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assertIsNotNone(barber.deleted_at)
        self.assertEqual(barber.deleted_by_id, self.admin.pk)
        self.assertTrue(Appointment.objects.filter(pk=appointment.pk).exists())

    def test_patch_reativar_restaura_perfil_e_limpa_soft_delete(self):
        user, barber = self.create_active_barber()
        self.client.force_authenticate(self.admin)
        self.client.patch(reverse('barber-detail', args=[barber.pk]), {'ativo': False}, format='json')

        response = self.client.patch(
            reverse('barber-detail', args=[barber.pk]), {'ativo': True}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        barber.refresh_from_db()
        user.refresh_from_db()
        self.assertTrue(barber.ativo)
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.BARBEIRO)
        self.assertIsNone(barber.deleted_at)
        self.assertIsNone(barber.deleted_by)

    def test_barbeiro_inativo_nao_enxerga_agenda_profissional(self):
        user, barber = self.create_active_barber()
        Appointment.objects.create(
            barbershop=self.shop, cliente=self.client_user, barbeiro=barber, servico=self.service,
            data_hora=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(self.admin)
        self.client.patch(reverse('barber-detail', args=[barber.pk]), {'ativo': False}, format='json')

        user.refresh_from_db()
        self.client.force_authenticate(user)
        response = self.client.get(reverse('appointment-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_isolamento_impede_criar_perfil_para_usuario_de_outra_barbearia(self):
        outsider = self.create_user('outra@example.com', User.TipoPerfil.CLIENTE, self.other_shop)
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse('barber-list'), {'user': outsider.pk, 'especialidade': 'Corte'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        outsider.refresh_from_db()
        self.assertEqual(outsider.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assertFalse(Barber.objects.filter(user=outsider).exists())

    def test_usuario_sem_perfil_barbeiro_ativo_nao_altera_agenda(self):
        user = self.create_user('sem-perfil@example.com', User.TipoPerfil.BARBEIRO, self.shop)
        _, active_barber = self.create_active_barber()
        appointment = Appointment.objects.create(
            barbershop=self.shop, cliente=self.client_user, barbeiro=active_barber, servico=self.service,
            data_hora=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(user)

        response = self.client.patch(
            reverse('appointment-detail', args=[appointment.pk]), {'observacoes': 'tentativa'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
