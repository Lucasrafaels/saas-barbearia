"""
Testes de permissões para o app accounts.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from barbershops.models import Barbershop
from .models import User

User = get_user_model()


class UserViewSetPermissionTests(APITestCase):
    """Testes de permissões para o UserViewSet."""

    def setUp(self):
        # Criar duas barbearias para teste de multi-tenancy
        self.barbershop1 = Barbershop.objects.create(
            nome='Barbearia 1',
            endereco='Rua 1, 123',
            telefone='11999999999',
            email='barb1@teste.com',
            horario_abertura='08:00',
            horario_fechamento='18:00'
        )
        self.barbershop2 = Barbershop.objects.create(
            nome='Barbearia 2',
            endereco='Rua 2, 456',
            telefone='11888888888',
            email='barb2@teste.com',
            horario_abertura='08:00',
            horario_fechamento='18:00'
        )

        # Criar usuários de cada papel na barbearia 1
        self.admin_user = User.objects.create_user(
            email='admin@teste.com',
            nome='Admin User',
            password='AdminPass123!',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop1
        )
        self.barbeiro_user = User.objects.create_user(
            email='barbeiro@teste.com',
            nome='Barbeiro User',
            password='BarbeiroPass123!',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop1
        )
        self.cliente_user = User.objects.create_user(
            email='cliente@teste.com',
            nome='Cliente User',
            password='ClientePass123!',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop1
        )
        # Cliente na barbearia 2 para teste de acesso cruzado
        self.cliente_user2 = User.objects.create_user(
            email='cliente2@teste.com',
            nome='Cliente User 2',
            password='ClientePass123!',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop2
        )

    def _get_auth_header(self, user):
        """Retorna header de autenticação JWT para o usuário."""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_admin_can_list_users_in_own_barbershop(self):
        """Admin deve conseguir listar usuários da própria barbearia."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Deve ver pelo menos os 3 usuários da barbearia 1
        self.assertGreaterEqual(len(response.data['results']), 3)

    def test_admin_cannot_list_users_in_other_barbershop(self):
        """Admin não deve conseguir listar usuários de outra barbearia."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que nenhum usuário da barbearia 2 está na lista
        for user in response.data['results']:
            self.assertNotEqual(user['email'], self.cliente_user2.email)

    def test_admin_can_retrieve_own_user(self):
        """Admin deve conseguir recuperar próprios dados."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.admin_user.email)

    def test_admin_can_update_own_user(self):
        """Admin deve conseguir atualizar próprios dados."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        data = {'nome': 'Admin Updated'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.nome, 'Admin Updated')

    def test_admin_can_update_other_user_in_same_barbershop(self):
        """Admin deve conseguir atualizar outros usuários da mesma barbearia."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-detail', kwargs={'pk': self.cliente_user.pk})
        data = {'nome': 'Cliente Updated'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente_user.refresh_from_db()
        self.assertEqual(self.cliente_user.nome, 'Cliente Updated')

    def test_admin_cannot_update_user_in_other_barbershop(self):
        """Admin não deve conseguir atualizar usuários de outra barbearia."""
        self.client.credentials(**self._get_auth_header(self.admin_user))
        url = reverse('user-detail', kwargs={'pk': self.cliente_user2.pk})
        data = {'nome': 'Hacked'}
        response = self.client.patch(url, data, format='json')
        # Deve retornar 404 porque o queryset filtra pela barbearia do admin
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_beireiro_can_only_access_own_user(self):
        """Barbeiro deve conseguir acessar apenas próprios dados."""
        self.client.credentials(**self._get_auth_header(self.barbeiro_user))
        url = reverse('user-detail', kwargs={'pk': self.barbeiro_user.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tentar acessar outro usuário: PER-13 (SEC-10), o mesmo 404 de um ID
        # inexistente (antes, 403 revelava que o ID existia).
        url = reverse('user-detail', kwargs={'pk': self.cliente_user.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_can_only_access_own_user(self):
        """Cliente deve conseguir acessar apenas próprios dados."""
        self.client.credentials(**self._get_auth_header(self.cliente_user))
        url = reverse('user-detail', kwargs={'pk': self.cliente_user.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tentar acessar outro usuário: PER-13 (SEC-10), o mesmo 404 de um ID
        # inexistente (antes, 403 revelava que o ID existia).
        url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_access_users(self):
        """Usuário não autenticado não deve conseguir acessar endpoints de usuários."""
        url = reverse('user-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)