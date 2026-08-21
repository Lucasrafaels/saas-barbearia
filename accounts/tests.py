from datetime import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from barbershops.models import Barbershop
from .models import User


class AccountsSecurityTests(APITestCase):
    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            nome='Administrador',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop,
        )
        self.client_user = User.objects.create_user(
            email='cliente@example.com',
            nome='Cliente',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        self.other_user = User.objects.create_user(
            email='outro@example.com',
            nome='Outro Cliente',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )

    def test_user_manager_creates_regular_and_super_users(self):
        user = User.objects.create_user(
            email='novo@example.com',
            nome='Novo Usuário',
            password='Senha-segura-123',
        )
        superuser = User.objects.create_superuser(
            email='root@example.com',
            nome='Root',
            password='Senha-segura-123',
        )

        self.assertTrue(user.check_password('Senha-segura-123'))
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_public_registration_creates_safe_initial_client_account(self):
        response = self.client.post(
            reverse('auth-register'),
            {
                'email': 'registro@example.com',
                'nome': 'Nova Pessoa',
                'password': 'Senha-segura-123',
                # Campos sensíveis não fazem parte do cadastro público.
                'tipo_perfil': User.TipoPerfil.ADMIN,
                'barbershop': self.barbershop.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='registro@example.com')
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assertIsNone(user.barbershop_id)
        self.assertTrue(user.check_password('Senha-segura-123'))

    def test_registration_rejects_weak_passwords(self):
        response = self.client.post(
            reverse('auth-register'),
            {
                'email': 'senha-fraca@example.com',
                'nome': 'Senha Fraca',
                'password': '1234567890',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(email='senha-fraca@example.com').exists())

    def test_only_admin_creates_tenant_users_with_safe_role_and_tenant(self):
        other_barbershop = Barbershop.objects.create(
            nome='Barbearia Externa',
            endereco='Rua Secundária, 200',
            telefone='11888888888',
            email='externa@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        url = reverse('user-list')
        self.client.force_authenticate(self.client_user)

        forbidden_response = self.client.post(
            url,
            {
                'email': 'nao-autorizado@example.com',
                'nome': 'Não Autorizado',
                'password': 'Senha-segura-123',
                'tipo_perfil': User.TipoPerfil.CLIENTE,
            },
            format='json',
        )

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        admin_role_response = self.client.post(
            url,
            {
                'email': 'admin-indevido@example.com',
                'nome': 'Admin Indevido',
                'password': 'Senha-segura-123',
                'tipo_perfil': User.TipoPerfil.ADMIN,
            },
            format='json',
        )
        self.assertEqual(admin_role_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tipo_perfil', admin_role_response.data)

        created_response = self.client.post(
            url,
            {
                'email': 'barbeiro-novo@example.com',
                'nome': 'Barbeiro Novo',
                'password': 'Senha-segura-123',
                'tipo_perfil': User.TipoPerfil.BARBEIRO,
                'barbershop': other_barbershop.pk,
            },
            format='json',
        )

        self.assertEqual(created_response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(email='barbeiro-novo@example.com')
        self.assertEqual(created_user.barbershop_id, self.barbershop.pk)
        self.assertEqual(created_user.tipo_perfil, User.TipoPerfil.BARBEIRO)

    def test_authenticated_creation_uses_password_validators(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse('user-list'),
            {
                'email': 'senha-fraca-interna@example.com',
                'nome': 'Senha Fraca Interna',
                'password': '1234567890',
                'tipo_perfil': User.TipoPerfil.CLIENTE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_client_cannot_read_or_edit_another_user_in_the_same_tenant(self):
        self.client.force_authenticate(self.client_user)
        url = reverse('user-detail', args=[self.other_user.pk])

        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(url, {'is_active': False}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.other_user.refresh_from_db()
        self.assertTrue(self.other_user.is_active)

    def test_client_can_edit_own_profile_and_admin_can_manage_tenant_users(self):
        self.client.force_authenticate(self.client_user)
        own_response = self.client.patch(
            reverse('user-detail', args=[self.client_user.pk]),
            {'nome': 'Cliente Atualizado'},
            format='json',
        )

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.patch(
            reverse('user-detail', args=[self.other_user.pk]),
            {'is_active': False},
            format='json',
        )

        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.other_user.refresh_from_db()
        self.assertFalse(self.other_user.is_active)
