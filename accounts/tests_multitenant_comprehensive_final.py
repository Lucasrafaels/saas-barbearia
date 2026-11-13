"""
Comprehensive multi-tenant isolation test suite - final corrected version.
"""
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from appointments.models import Appointment
from datetime import time, timedelta
from django.utils import timezone


class ComprehensiveMultiTenantIsolationTests(APITestCase):
    """Exhaustive multi-tenant isolation tests following working patterns."""

    def setUp(self):
        # Create two tenants
        self.shop_a = self.create_barbershop('Barbearia A', 'a@example.com')
        self.shop_b = self.create_barbershop('Barbearia B', 'b@example.com')

        # Create users in each tenant
        self.admin_a = self.create_user('admin-a@example.com', User.TipoPerfil.ADMIN, self.shop_a)
        self.client_a = self.create_user('client-a@example.com', User.TipoPerfil.CLIENTE, self.shop_a)
        self.barber_user_a = self.create_user('barber-a@example.com', User.TipoPerfil.BARBEIRO, self.shop_a)
        self.barber_a = Barber.objects.create(user=self.barber_user_a, barbershop=self.shop_a, ativo=True)

        self.admin_b = self.create_user('admin-b@example.com', User.TipoPerfil.ADMIN, self.shop_b)
        self.client_b = self.create_user('client-b@example.com', User.TipoPerfil.CLIENTE, self.shop_b)
        self.barber_user_b = self.create_user('barber-b@example.com', User.TipoPerfil.BARBEIRO, self.shop_b)
        self.barber_b = Barber.objects.create(user=self.barber_user_b, barbershop=self.shop_b, ativo=True)

        # Create services
        self.service_a = Service.objects.create(
            barbershop=self.shop_a, nome='Service A', preco='50.00', duracao=30, ativo=True
        )
        self.service_b = Service.objects.create(
            barbershop=self.shop_b, nome='Service B', preco='60.00', duracao=30, ativo=True
        )

        # Create appointments - make sure they don't conflict for deletion tests
        start_a = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        start_b = (timezone.localtime() + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0)
        self.appointment_a = Appointment.objects.create(
            barbershop=self.shop_a,
            cliente=self.client_a,
            barbeiro=self.barber_a,
            servico=self.service_a,
            data_hora=start_a,
            status=Appointment.Status.AGENDADO,
        )
        self.appointment_b = Appointment.objects.create(
            barbershop=self.shop_b,
            cliente=self.client_b,
            barbeiro=self.barber_b,
            servico=self.service_b,
            data_hora=start_b,
            status=Appointment.Status.AGENDADO,
        )

        # Superuser
        self.superuser = User.objects.create_superuser(
            email='root@example.com', nome='Super User', password='Senha-segura-123'
        )

    def create_barbershop(self, nome, email):
        return Barbershop.objects.create(
            nome=nome,
            endereco=f'Rua {nome}, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )

    def create_user(self, email, tipo_perfil, barbershop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=barbershop,
        )

    # Test user isolation patterns from working tests
    def test_user_isolation_comprehensive(self):
        """Test user CRUD isolation using patterns from working test suite."""
        # Test that users from tenant B don't appear in tenant A's list
        self.client.force_authenticate(self.admin_a)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [user['id'] for user in response.data['results']]
        self.assertIn(self.admin_a.id, ids)
        self.assertIn(self.client_a.id, ids)
        self.assertIn(self.barber_user_a.id, ids)
        self.assertNotIn(self.admin_b.id, ids)
        self.assertNotIn(self.client_b.id, ids)
        self.assertNotIn(self.barber_user_b.id, ids)

        # Test that retrieving other tenant's user returns 404
        url = reverse('user-detail', args=[self.admin_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test that creating user ignores barbershop in payload
        payload = {
            'email': 'hack@example.com',
            'nome': 'Hacked User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
            'barbershop': self.shop_b.id,  # Try to assign to tenant B
        }
        response = self.client.post(reverse('user-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Should be tenant A

        # Test that updating user cannot change barbershop
        user.barbershop_id = self.shop_a.id  # Ensure it's correct
        url = reverse('user-detail', args=[user.id])
        payload = {'barbershop': self.shop_b.id}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Unchanged

    # Test barber isolation
    def test_barber_isolation_comprehensive(self):
        """Test barber CRUD isolation."""
        self.client.force_authenticate(self.admin_a)

        # Test list isolation
        response = self.client.get(reverse('barber-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [barber['id'] for barber in response.data['results']]
        self.assertIn(self.barber_a.id, ids)
        self.assertNotIn(self.barber_b.id, ids)

        # Test retrieve other tenant returns 404
        url = reverse('barber-detail', args=[self.barber_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test create ignores barbershop
        barber_user = self.create_user('barber-hack@example.com', User.TipoPerfil.BARBEIRO, self.shop_a)
        payload = {
            'user': barber_user.id,
            'barbershop': self.shop_b.id,  # Try to assign to tenant B
            'ativo': True,
        }
        response = self.client.post(reverse('barber-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        barber = Barber.objects.get(id=response.data['id'])
        self.assertEqual(barber.barbershop_id, self.shop_a.id)  # Should be tenant A

        # Test update cannot change barbershop (read-only)
        barber.barbershop_id = self.shop_a.id  # Reset
        url = reverse('barber-detail', args=[barber.id])
        payload = {'barbershop': self.shop_b.id}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        barber.refresh_from_db()
        self.assertEqual(barber.barbershop_id, self.shop_a.id)  # Unchanged

    # Test service isolation
    def test_service_isolation_comprehensive(self):
        """Test service CRUD isolation."""
        self.client.force_authenticate(self.admin_a)

        # Test list isolation
        response = self.client.get(reverse('service-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [service['id'] for service in response.data['results']]
        self.assertIn(self.service_a.id, ids)
        self.assertNotIn(self.service_b.id, ids)

        # Test retrieve other tenant returns 404
        url = reverse('service-detail', args=[self.service_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test create ignores barbershop
        payload = {
            'nome': 'Hacked Service',
            'preco': '70.00',
            'duracao': 45,
            'barbershop': self.shop_b.id,  # Try to assign to tenant B
            'ativo': True,
        }
        response = self.client.post(reverse('service-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service = Service.objects.get(id=response.data['id'])
        self.assertEqual(service.barbershop_id, self.shop_a.id)  # Should be tenant A

        # Test update (nome change)
        url = reverse('service-detail', args=[self.service_a.id])
        payload = {'nome': 'Updated Service A'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service_a.refresh_from_db()
        self.assertEqual(self.service_a.nome, 'Updated Service A')

        # Test delete (soft delete) - use a service not referenced by appointments
        service_to_delete = Service.objects.create(
            barbershop=self.shop_a,
            nome='Service To Delete',
            preco='30.00',
            duracao=15,
            ativo=True
        )
        url = reverse('service-detail', args=[service_to_delete.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        service_to_delete.refresh_from_db()
        self.assertFalse(service_to_delete.ativo)

    # Test appointment isolation (based on working appointment tests)
    def test_appointment_isolation_comprehensive(self):
        """Test appointment CRUD isolation."""
        self.client.force_authenticate(self.admin_a)

        # Test list isolation
        response = self.client.get(reverse('appointment-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [appt['id'] for appt in response.data['results']]
        self.assertIn(self.appointment_a.id, ids)
        self.assertNotIn(self.appointment_b.id, ids)

        # Test retrieve other tenant returns 404
        url = reverse('appointment-detail', args=[self.appointment_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test create with cross-tenant foreign keys fails
        payload = {
            'cliente': self.client_b.id,  # Tenant B client
            'barbeiro': self.barber_a.id,  # Tenant A barber
            'servico': self.service_a.id,  # Tenant A service
            'data_hora': (timezone.localtime() + timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat(),
        }
        response = self.client.post(reverse('appointment-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)  # Should fail validation

        # Test create ignores barbershop field
        payload = {
            'cliente': self.client_a.id,
            'barbeiro': self.barber_a.id,
            'servico': self.service_a.id,
            'data_hora': (timezone.localtime() + timedelta(days=2)).replace(hour=16, minute=0, second=0, microsecond=0).isoformat(),
            'barbershop': self.shop_b.id,  # Try to force tenant B
        }
        response = self.client.post(reverse('appointment-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get(id=response.data['id'])
        self.assertEqual(appointment.barbershop_id, self.shop_a.id)  # Should be tenant A

        # Test update cannot change relationships to other tenant
        url = reverse('appointment-detail', args=[self.appointment_a.id])
        payload = {
            'cliente': self.client_b.id,  # Try to change to tenant B client
            'observacoes': 'Hacked',
        }
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.appointment_a.refresh_from_db()
        self.assertEqual(self.appointment_a.cliente_id, self.client_a.id)  # Unchanged
        self.assertNotEqual(self.appointment_a.observacoes, 'Hacked')  # Not updated

        # Test update same-tenant fields works
        payload = {'observacoes': 'Legitimate update'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment_a.refresh_from_db()
        self.assertEqual(self.appointment_a.observacoes, 'Legitimate update')

        # Test delete (cancel) works for same tenant - use appointment without service conflicts
        appointment_to_delete = Appointment.objects.create(
            barbershop=self.shop_a,
            cliente=self.client_a,
            barbeiro=self.barber_a,
            servico=Service.objects.create(
                barbershop=self.shop_a,
                nome='Delete Service',
                preco='20.00',
                duracao=15,
                ativo=True
            ),
            data_hora=timezone.localtime() + timedelta(days=3),
            status=Appointment.Status.AGENDADO,
        )
        url = reverse('appointment-detail', args=[appointment_to_delete.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        appointment_to_delete.refresh_from_db()
        self.assertEqual(appointment_to_delete.status, Appointment.Status.CANCELADO)

    # Test role-based access within tenant
    def test_role_based_access_within_tenant(self):
        """Test that roles work correctly within same tenant."""
        # Test client cannot create services
        self.client.force_authenticate(self.client_a)
        payload = {
            'nome': 'Client Service',
            'preco': '30.00',
            'duracao': 15,
            'ativo': True,
        }
        response = self.client.post(reverse('service-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test barber cannot create services
        self.client.force_authenticate(self.barber_user_a)
        response = self.client.post(reverse('service-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test admin can create services
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(reverse('service-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Test superuser access
    def test_superuser_can_access_all_tenants(self):
        """Test that superuser can access all tenant data."""
        self.client.force_authenticate(self.superuser)

        # Can list users from both tenants
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [user['id'] for user in response.data['results']]
        self.assertIn(self.admin_a.id, ids)
        self.assertIn(self.admin_b.id, ids)

        # Can retrieve user from tenant B
        url = reverse('user-detail', args=[self.admin_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can update user from tenant B
        url = reverse('user-detail', args=[self.admin_b.id])
        payload = {'nome': 'Hacked by superuser'}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_b.refresh_from_db()
        self.assertEqual(self.admin_b.nome, 'Hacked by superuser')

        # Can delete user from tenant B. admin_b é o único admin ativo da
        # barbearia B e não pode ser desativado (BUS-01); um cliente pode.
        url = reverse('user-detail', args=[self.admin_b.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.delete(reverse('user-detail', args=[self.client_b.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # Test anonymous access denied
    def test_anonymous_access_denied(self):
        """Test that anonymous users cannot access endpoints."""
        self.client.force_authenticate(user=None)
        endpoints = [
            reverse('user-list'),
            reverse('barber-list'),
            reverse('service-list'),
            reverse('appointment-list'),
        ]
        for url in endpoints:
            with self.subTest(endpoint=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # Test user without barbershop sees no data
    def test_user_without_barbershop_sees_no_data(self):
        """Test that users without barbershop see empty lists."""
        orphan_admin = User.objects.create_user(
            email='orphan@example.com',
            nome='Orphan Admin',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=None,
        )
        self.client.force_authenticate(orphan_admin)
        endpoints = [
            reverse('user-list'),
            reverse('barber-list'),
            reverse('service-list'),
            reverse('appointment-list'),
        ]
        for url in endpoints:
            with self.subTest(endpoint=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data['results']), 0)

    # Test filter/search isolation
    def test_filter_search_isolation(self):
        """Test that filters cannot access other tenant data."""
        self.client.force_authenticate(self.admin_a)

        # Test filtering by other tenant's barber returns empty/not found
        response = self.client.get(reverse('appointment-list'), {'barbeiro': self.barber_b.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [appt['id'] for appt in response.data['results']]
        self.assertNotIn(self.appointment_b.id, ids)

        # Test filtering by other tenant's service returns empty/not found
        response = self.client.get(reverse('appointment-list'), {'servico': self.service_b.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [appt['id'] for appt in response.data['results']]
        self.assertNotIn(self.appointment_b.id, ids)

    # Test manual tenant injection attacks
    def test_manual_tenant_injection_attacks(self):
        """Test various manual tenant ID injection attempts."""
        self.client.force_authenticate(self.admin_a)

        # Test user creation with multiple tenant ID fields
        payload = {
            'email': 'injection@example.com',
            'nome': 'Injection User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
            'barbershop': self.shop_b.id,
            'barbershop_id': self.shop_b.id,
            'tenant_id': self.shop_b.id,
        }
        response = self.client.post(reverse('user-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Should be ignored

        # Test barber creation with injection
        barber_user = self.create_user('barber-inject@example.com', User.TipoPerfil.BARBEIRO, self.shop_a)
        payload = {
            'user': barber_user.id,
            'barbershop': self.shop_b.id,
            'barbershop_id': self.shop_b.id,
            'tenant_id': self.shop_b.id,
            'ativo': True,
        }
        response = self.client.post(reverse('barber-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        barber = Barber.objects.get(id=response.data['id'])
        self.assertEqual(barber.barbershop_id, self.shop_a.id)  # Should be ignored

        # Test service creation with injection
        payload = {
            'nome': 'Injection Service',
            'preco': '40.00',
            'duracao': 20,
            'barbershop': self.shop_b.id,
            'barbershop_id': self.shop_b.id,
            'tenant_id': self.shop_b.id,
            'ativo': True,
        }
        response = self.client.post(reverse('service-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service = Service.objects.get(id=response.data['id'])
        self.assertEqual(service.barbershop_id, self.shop_a.id)  # Should be ignored