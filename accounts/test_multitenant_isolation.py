"""Multi-tenant isolation tests for accounts app."""
from datetime import time
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barbershop


class AccountMultiTenantIsolationTests(APITestCase):
    """Test multi-tenant isolation for User endpoints."""

    def setUp(self):
        self.shop_a = self.create_shop('Barbearia A', 'a@example.com')
        self.shop_b = self.create_shop('Barbearia B', 'b@example.com')

        self.admin_a = self.create_user('admin-a@example.com', User.TipoPerfil.ADMIN, self.shop_a)
        self.barber_a = self.create_user('barber-a@example.com', User.TipoPerfil.BARBEIRO, self.shop_a)
        self.client_a = self.create_user('client-a@example.com', User.TipoPerfil.CLIENTE, self.shop_a)

        self.admin_b = self.create_user('admin-b@example.com', User.TipoPerfil.ADMIN, self.shop_b)
        self.barber_b = self.create_user('barber-b@example.com', User.TipoPerfil.BARBEIRO, self.shop_b)
        self.client_b = self.create_user('client-b@example.com', User.TipoPerfil.CLIENTE, self.shop_b)

        # Superuser (no tenant)
        self.superuser = User.objects.create_superuser(
            email='root@example.com', nome='Root', password='Senha-segura-123'
        )

        self.client.force_authenticate(self.admin_a)

    @staticmethod
    def create_shop(name, email):
        return Barbershop.objects.create(
            nome=name,
            endereco='Rua dos Testes, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(8, 0),
            horario_fechamento=time(18, 0),
        )

    @staticmethod
    def create_user(email, perfil, shop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=perfil,
            barbershop=shop,
        )

    def test_user_list_does_not_expose_other_tenant_users(self):
        """Users from tenant B should not appear in tenant A's user list."""
        self.client.force_authenticate(self.admin_a)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [user['id'] for user in response.data['results']]
        self.assertNotIn(self.admin_b.id, ids)
        self.assertNotIn(self.barber_b.id, ids)
        self.assertNotIn(self.client_b.id, ids)

    def test_user_retrieve_other_tenant_returns_404(self):
        """Retrieving a user from another tenant returns 404."""
        self.client.force_authenticate(self.admin_a)
        url = reverse('user-detail', args=[self.admin_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_create_is_forced_to_requesters_tenant(self):
        """Creating a user ignores barbershop in payload and uses requester's tenant."""
        self.client.force_authenticate(self.admin_a)
        payload = {
            'email': 'new@example.com',
            'nome': 'New User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
            'barbershop': self.shop_b.id,  # Attempt to assign to tenant B
        }
        response = self.client.post(reverse('user-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Should be tenant A

    def test_user_update_cannot_change_barbershop(self):
        """Updating a user cannot change barbershop (read-only)."""
        self.client.force_authenticate(self.admin_a)
        url = reverse('user-detail', args=[self.client_a.id])
        payload = {'barbershop': self.shop_b.id}
        response = self.client.patch(url, payload, format='json')
        # Should succeed (200) but barbershop unchanged
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_a.refresh_from_db()
        self.assertEqual(self.client_a.barbershop_id, self.shop_a.id)

    def test_user_update_cannot_change_tipo_perfil_to_admin_via_serializer(self):
        """Ninguém consegue conceder papel de admin via PATCH /users/{id}/."""
        # accounts/serializers.py:UserSerializer torna 'tipo_perfil' read_only
        # para quem não é admin - ou seja, se o ator for barber_a/client_a,
        # o campo é simplesmente ignorado (200, sem mudança), sem nunca
        # chegar em validate_tipo_perfil(). Para de fato exercitar a
        # validação do serializer (que bloqueia ATÉ o próprio admin de
        # conceder papel de admin por este endpoint - ver docstring de
        # UserSerializer.validate_tipo_perfil), o ator precisa ser admin.
        self.client.force_authenticate(self.admin_a)
        url = reverse('user-detail', args=[self.client_a.id])
        payload = {'tipo_perfil': User.TipoPerfil.ADMIN}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.client_a.refresh_from_db()
        self.assertNotEqual(self.client_a.tipo_perfil, User.TipoPerfil.ADMIN)

    def test_admin_can_manage_users_in_same_tenant(self):
        """Admin can list, create, retrieve, update, delete users in same tenant."""
        self.client.force_authenticate(self.admin_a)
        # List
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 3)  # admin_a, barber_a, client_a
        # Create
        payload = {
            'email': 'new@example.com',
            'nome': 'New User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        response = self.client.post(reverse('user-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data['id']
        # Retrieve
        url = reverse('user-detail', args=[user_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Update
        payload = {'nome': 'Updated Name'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Delete
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_cannot_manage_users_in_other_tenant(self):
        """Admin cannot perform any operation on users from another tenant."""
        self.client.force_authenticate(self.admin_a)
        target_id = self.admin_b.id
        # List (already tested in test_user_list_does_not_expose_other_tenant_users)
        # Retrieve
        url = reverse('user-detail', args=[target_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Update
        payload = {'nome': 'Hacked'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Delete
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_barber_cannot_manage_users(self):
        """Barber role cannot access user endpoints (except own retrieve/update)."""
        self.client.force_authenticate(self.barber_a)
        # A listagem (GET /users/) é restrita a admin/superuser (IsAdminRole em
        # UserViewSet.get_permissions); um barbeiro não pode listar usuários,
        # nem os da própria barbearia. Ver accounts/test_permissions.py, que
        # cobre o mesmo comportamento de acesso restrito por papel.
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Retrieve own user
        url = reverse('user-detail', args=[self.barber_a.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Retrieve other user na mesma barbearia: PER-13 (SEC-10). Na leitura
        # de detalhe, o barbeiro só enxerga o próprio cadastro já na consulta,
        # e recebe o mesmo 404 de um ID inexistente (antes, 403 revelava que o
        # ID existia). Ver accounts/test_per13.py.
        url = reverse('user-detail', args=[self.client_a.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Update own user (allowed? IsSelfOrAdmin allows update of own)
        url = reverse('user-detail', args=[self.barber_a.id])
        payload = {'nome': 'New Name'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Update other user (should be 403 or 404)
        url = reverse('user-detail', args=[self.client_a.id])
        response = self.client.patch(url, payload, format='json')
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_client_cannot_manage_users(self):
        """Client role cannot access user endpoints."""
        self.client.force_authenticate(self.client_a)
        # List (restrito a admin/superuser - ver test_barber_cannot_manage_users)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Retrieve own
        url = reverse('user-detail', args=[self.client_a.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Retrieve other (mesma barbearia): PER-13 (SEC-10), o mesmo 404 de um
        # ID inexistente, sem carregar o registro. Ver accounts/test_per13.py.
        url = reverse('user-detail', args=[self.admin_a.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Update own (allowed? IsSelfOrAdmin)
        url = reverse('user-detail', args=[self.client_a.id])
        payload = {'nome': 'New Name'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Update other
        url = reverse('user-detail', args=[self.admin_a.id])
        response = self.client.patch(url, payload, format='json')
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_superuser_can_access_all_users(self):
        """Superuser can access users from any tenant."""
        self.client.force_authenticate(self.superuser)
        # List all users
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see at least 6 users (2 admins, 2 barbers, 2 clients)
        self.assertGreaterEqual(len(response.data['results']), 6)
        # Retrieve user from tenant B
        url = reverse('user-detail', args=[self.admin_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Update user from tenant B
        payload = {'nome': 'Hacked by superuser'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_b.refresh_from_db()
        self.assertEqual(self.admin_b.nome, 'Hacked by superuser')
        # Delete user from tenant B. admin_b é o único admin ativo da
        # barbearia B e não pode ser desativado (BUS-01); um cliente pode.
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.delete(reverse('user-detail', args=[self.client_b.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_anonymous_user_cannot_access_user_endpoints(self):
        """Anonymous users get 401 on user endpoints."""
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(reverse('user-list'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_set_barbershop_via_create_payload(self):
        """Attempt to set barbershop during creation is ignored."""
        self.client.force_authenticate(self.admin_a)
        payload = {
            'email': 'test@example.com',
            'nome': 'Test User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
            'barbershop': self.shop_b.id,
            'barbershop_id': self.shop_b.id,
            'tenant_id': self.shop_b.id,
        }
        response = self.client.post(reverse('user-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertEqual(user.barbershop_id, self.shop_a.id)

    def test_admin_without_tenant_sees_no_users(self):
        """Admin without a barbershop sees empty user list."""
        admin_no_tenant = User.objects.create_user(
            email='orphan@example.com',
            nome='Orphan Admin',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=None,
        )
        self.client.force_authenticate(admin_no_tenant)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)