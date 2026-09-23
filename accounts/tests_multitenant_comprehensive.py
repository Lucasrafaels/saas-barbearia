"""
Comprehensive multi-tenant isolation test suite.
Tests all entities, roles, operations, and attack vectors for tenant isolation.
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
from decimal import Decimal


class ComprehensiveMultiTenantIsolationTests(APITestCase):
    """Exhaustive multi-tenant isolation tests for all entities and roles."""

    @classmethod
    def setUpTestData(cls):
        """Create tenants and users for all test methods."""
        # Tenant A
        cls.shop_a = Barbershop.objects.create(
            nome='Barbearia A',
            endereco='Rua A, 100',
            telefone='11900000001',
            email='a@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        # Tenant B
        cls.shop_b = Barbershop.objects.create(
            nome='Barbearia B',
            endereco='Rua B, 200',
            telefone='11900000002',
            email='b@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )

        # Users in Tenant A
        cls.admin_a = User.objects.create_user(
            email='admin-a@example.com',
            nome='Admin A',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=cls.shop_a,
        )
        cls.barber_a = User.objects.create_user(
            email='barber-a@example.com',
            nome='Barber A',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_a,
        )
        cls.client_a = User.objects.create_user(
            email='client-a@example.com',
            nome='Client A',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=cls.shop_a,
        )

        # Users in Tenant B
        cls.admin_b = User.objects.create_user(
            email='admin-b@example.com',
            nome='Admin B',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=cls.shop_b,
        )
        cls.barber_b = User.objects.create_user(
            email='barber-b@example.com',
            nome='Barber B',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_b,
        )
        cls.client_b = User.objects.create_user(
            email='client-b@example.com',
            nome='Client B',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=cls.shop_b,
        )

        # Superuser (no tenant)
        cls.superuser = User.objects.create_superuser(
            email='root@example.com',
            nome='Super User',
            password='Senha-segura-123',
        )

        # Barber profiles
        cls.barber_profile_a = Barber.objects.create(
            user=cls.barber_a,
            barbershop=cls.shop_a,
            ativo=True,
        )
        cls.barber_profile_b = Barber.objects.create(
            user=cls.barber_b,
            barbershop=cls.shop_b,
            ativo=True,
        )

        # Services
        cls.service_a = Service.objects.create(
            barbershop=cls.shop_a,
            nome='Service A',
            preco=Decimal('50.00'),
            duracao=30,
            ativo=True,
        )
        cls.service_b = Service.objects.create(
            barbershop=cls.shop_b,
            nome='Service B',
            preco=Decimal('60.00'),
            duracao=30,
            ativo=True,
        )

        # Appointments
        cls.appointment_a = Appointment.objects.create(
            barbershop=cls.shop_a,
            cliente=cls.client_a,
            barbeiro=cls.barber_profile_a,
            servico=cls.service_a,
            data_hora=timezone.now() + timedelta(days=1),
            status=Appointment.Status.AGENDADO,
        )
        cls.appointment_b = Appointment.objects.create(
            barbershop=cls.shop_b,
            cliente=cls.client_b,
            barbeiro=cls.barber_profile_b,
            servico=cls.service_b,
            data_hora=timezone.now() + timedelta(days=1),
            status=Appointment.Status.AGENDADO,
        )

        # URLs
        cls.user_list_url = reverse('user-list')
        cls.barber_list_url = reverse('barber-list')
        cls.service_list_url = reverse('service-list')
        cls.appointment_list_url = reverse('appointment-list')

    def setUp(self):
        """Reset client authentication before each test."""
        self.client.force_authenticate(user=None)

    # Helper methods
    def _user_detail_url(self, user_id):
        return reverse('user-detail', args=[user_id])

    def _barber_detail_url(self, barber_id):
        return reverse('barber-detail', args=[barber_id])

    def _service_detail_url(self, service_id):
        return reverse('service-detail', args=[service_id])

    def _appointment_detail_url(self, appointment_id):
        return reverse('appointment-detail', args=[appointment_id])

    def _valid_user_payload(self, **overrides):
        payload = {
            'email': 'new@example.com',
            'nome': 'New User',
            'password': 'Senha-segura-123',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        payload.update(overrides)
        return payload

    def _valid_barber_payload(self, **overrides):
        payload = {
            'ativo': True,
        }
        payload.update(overrides)
        return payload

    def _valid_service_payload(self, **overrides):
        payload = {
            'nome': 'New Service',
            'preco': '55.00',
            'duracao': 45,
            'ativo': True,
        }
        payload.update(overrides)
        return payload

    def _valid_appointment_payload(self, **overrides):
        payload = {
            'cliente': self.client_a.pk,
            'barbeiro': self.barber_profile_a.pk,
            'servico': self.service_a.pk,
            'data_hora': (timezone.now() + timedelta(days=1)).isoformat(),
        }
        payload.update(overrides)
        return payload

    # ========== USER ENDPOINT TESTS ==========

    def test_user_crud_isolation_by_role_and_tenant(self):
        """Test User CRUD operations for all role/tenant combinations."""
        test_cases = [
            # (actor, actor_tenant, target_user, target_tenant, expected_status_codes)
            # Format: (actor_user, actor_desc, target_user, target_desc,
            #          list_ok, retrieve_ok, create_ok, update_ok, delete_ok)
            (self.admin_a, 'Admin A', self.admin_a, 'Admin A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.admin_a, 'Admin A', self.admin_b, 'Admin B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_201_CREATED,
             status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
            (self.barber_a, 'Barber A', self.admin_a, 'Admin A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            (self.barber_a, 'Barber A', self.admin_b, 'Admin B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.admin_a, 'Admin A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.admin_b, 'Admin B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.superuser, 'Superuser', self.admin_a, 'Admin A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.admin_b, 'Admin B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
        ]

        for actor, actor_desc, target_user, target_desc, list_ok, retrieve_ok, create_ok, update_ok, delete_ok in test_cases:
            with self.subTest(actor=actor_desc, target=target_desc):
                self.client.force_authenticate(actor)

                # LIST - should only show users from actor's tenant (or all for superuser)
                response = self.client.get(self.user_list_url)
                self.assertEqual(response.status_code, list_ok,
                               f"List failed for {actor_desc}")
                if list_ok == status.HTTP_200_OK:
                    ids = [u['id'] for u in response.data['results']]
                    if actor == self.superuser:
                        # Superuser sees all users
                        self.assertIn(target_user.id, ids)
                    elif actor.barbershop_id == target_user.barbershop_id:
                        # Same tenant
                        self.assertIn(target_user.id, ids)
                    else:
                        # Different tenant
                        self.assertNotIn(target_user.id, ids)

                # RETRIEVE
                url = self._user_detail_url(target_user.id)
                response = self.client.get(url)
                self.assertEqual(response.status_code, retrieve_ok,
                               f"Retrieve failed for {actor_desc} -> {target_desc}")

                # CREATE (only test if actor can create users)
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN):
                    payload = self._valid_user_payload(
                        email=f'test-{actor.pk}@{target_user.pk}.com',
                        nome=f'Test {actor.nome}',
                        tipo_perfil=User.TipoPerfil.CLIENTE,
                    )
                    # Try to force barbershop to target's tenant (should be ignored for non-admin)
                    payload['barbershop'] = target_user.barbershop_id
                    response = self.client.post(self.user_list_url, payload, format='json')
                    self.assertEqual(response.status_code, create_ok,
                                   f"Create failed for {actor_desc}")
                    if create_ok == status.HTTP_201_CREATED:
                        # Verify created user is in actor's tenant, not target's
                        created_user = User.objects.get(id=response.data['id'])
                        self.assertEqual(created_user.barbershop_id, actor.barbershop_id)

                # UPDATE
                if update_ok in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._user_detail_url(target_user.id)
                    payload = {'nome': f'Updated {target_user.nome}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_user.refresh_from_db()
                        self.assertEqual(target_user.nome, f'Updated {target_user.nome.split()[0]}')
                    elif update_ok == status.HTTP_200_OK and actor == target_user:
                        # Self-update should work
                        target_user.refresh_from_db()
                        self.assertEqual(target_user.nome, f'Updated {target_user.nome.split()[0]}')

                # DELETE
                if delete_ok in (status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._user_detail_url(target_user.id)
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_ok,
                                   f"Delete failed for {actor_desc} -> {target_desc}")

    def test_user_manual_tenant_injection_attacks(self):
        """Test that specifying barbershop_id in payload is ignored."""
        # Admin A tries to create user with barbershop_id of Tenant B
        self.client.force_authenticate(self.admin_a)
        payload = self._valid_user_payload(
            email='hack@example.com',
            nome='Hacked User',
            barbershop=self.shop_b.id,  # Attempt to assign to Tenant B
            barbershop_id=self.shop_b.id,
        )
        response = self.client.post(self.user_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Should be Tenant A

        # Try to update user's barbershop (should be ignored/read-only)
        user.barbershop_id = self.shop_a.id  # Reset
        url = self._user_detail_url(user.id)
        payload = {'barbershop': self.shop_b.id}
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.barbershop_id, self.shop_a.id)  # Unchanged

    # ========== BARBER ENDPOINT TESTS ==========

    def test_barber_crud_isolation(self):
        """Test Barber CRUD operations for isolation."""
        test_cases = [
            # (actor, target_barber_profile, expected_status_codes)
            # (actor_user, actor_desc, target_barber_profile, target_desc, list_ok, retrieve_ok, create_ok, update_ok, delete_ok)
            (self.admin_a, 'Admin A', self.barber_profile_a, 'Barber A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.admin_a, 'Admin A', self.barber_profile_b, 'Barber B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_201_CREATED,
             status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
            (self.barber_a, 'Barber A', self.barber_profile_a, 'Barber A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            (self.barber_a, 'Barber A', self.barber_profile_b, 'Barber B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.superuser, 'Superuser', self.barber_profile_a, 'Barber A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.barber_profile_b, 'Barber B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
        ]

        for actor, actor_desc, target_profile, target_desc, list_ok, retrieve_ok, create_ok, update_ok, delete_ok in test_cases:
            with self.subTest(actor=actor_desc, target=target_desc):
                self.client.force_authenticate(actor)

                # LIST
                response = self.client.get(self.barber_list_url)
                self.assertEqual(response.status_code, list_ok,
                               f"Barber list failed for {actor_desc}")
                if list_ok == status.HTTP_200_OK:
                    ids = [b['id'] for b in response.data['results']]
                    if actor == self.superuser:
                        self.assertIn(target_profile.id, ids)
                    elif actor.barbershop_id == target_profile.barbershop_id:
                        self.assertIn(target_profile.id, ids)
                    else:
                        self.assertNotIn(target_profile.id, ids)

                # RETRIEVE
                url = self._barber_detail_url(target_profile.id)
                response = self.client.get(url)
                self.assertEqual(response.status_code, retrieve_ok,
                               f"Barber retrieve failed for {actor_desc} -> {target_desc}")

                # CREATE
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN):
                    payload = self._valid_barber_payload()
                    # Try to force barbershop
                    payload['barbershop'] = target_profile.barbershop.id
                    response = self.client.post(self.barber_list_url, payload, format='json')
                    self.assertEqual(response.status_code, create_ok,
                                   f"Barber create failed for {actor_desc}")
                    if create_ok == status.HTTP_201_CREATED:
                        barber = Barber.objects.get(id=response.data['id'])
                        self.assertEqual(barber.barbershop_id, actor.barbershop_id)

                # UPDATE
                if update_ok in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._barber_detail_url(target_profile.id)
                    payload = {'ativo': not target_profile.ativo}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Barber update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_profile.refresh_from_db()
                        self.assertEqual(target_profile.ativo, not target_profile.ativo)

                # DELETE
                if delete_ok in (status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._barber_detail_url(target_profile.id)
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_ok,
                                   f"Barber delete failed for {actor_desc} -> {target_desc}")

    # ========== SERVICE ENDPOINT TESTS ==========

    def test_service_crud_isolation(self):
        """Test Service CRUD operations for isolation."""
        test_cases = [
            # (actor, target_service, expected_status_codes)
            (self.admin_a, 'Admin A', self.service_a, 'Service A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.admin_a, 'Admin A', self.service_b, 'Service B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_201_CREATED,
             status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
            (self.barber_a, 'Barber A', self.service_a, 'Service A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.barber_a, 'Barber A', self.service_b, 'Service B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.service_a, 'Service A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.service_b, 'Service B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.superuser, 'Superuser', self.service_a, 'Service A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.service_b, 'Service B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
        ]

        for actor, actor_desc, target_service, target_desc, list_ok, retrieve_ok, create_ok, update_ok, delete_ok in test_cases:
            with self.subTest(actor=actor_desc, target=target_desc):
                self.client.force_authenticate(actor)

                # LIST
                response = self.client.get(self.service_list_url)
                self.assertEqual(response.status_code, list_ok,
                               f"Service list failed for {actor_desc}")
                if list_ok == status.HTTP_200_OK:
                    ids = [s['id'] for s in response.data['results']]
                    if actor == self.superuser:
                        self.assertIn(target_service.id, ids)
                    elif actor.barbershop_id == target_service.barbershop_id:
                        self.assertIn(target_service.id, ids)
                    else:
                        self.assertNotIn(target_service.id, ids)

                # RETRIEVE
                url = self._service_detail_url(target_service.id)
                response = self.client.get(url)
                self.assertEqual(response.status_code, retrieve_ok,
                               f"Service retrieve failed for {actor_desc} -> {target_desc}")

                # CREATE
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN):
                    payload = self._valid_service_payload(
                        nome=f'Service from {actor.nome}',
                    )
                    # Try to force barbershop
                    payload['barbershop'] = target_service.barbershop.id
                    response = self.client.post(self.service_list_url, payload, format='json')
                    self.assertEqual(response.status_code, create_ok,
                                   f"Service create failed for {actor_desc}")
                    if create_ok == status.HTTP_201_CREATED:
                        service = Service.objects.get(id=response.data['id'])
                        self.assertEqual(service.barbershop_id, actor.barbershop_id)

                # UPDATE
                if update_ok in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._service_detail_url(target_service.id)
                    payload = {'nome': f'Updated {target_service.nome}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Service update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_service.refresh_from_db()
                        self.assertEqual(target_service.nome, f'Updated {target_service.nome.split()[0]}')

                # DELETE (soft delete)
                if delete_ok in (status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._service_detail_url(target_service.id)
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_ok,
                                   f"Service delete failed for {actor_desc} -> {target_desc}")
                    if delete_ok == status.HTTP_204_NO_CONTENT:
                        target_service.refresh_from_db()
                        self.assertFalse(target_service.ativo)

    def test_service_manual_tenant_injection_attacks(self):
        """Test that specifying barbershop_id in service payload is ignored."""
        # Admin A tries to create service with barbershop_id of Tenant B
        self.client.force_authenticate(self.admin_a)
        payload = self._valid_service_payload(
            nome='Hacked Service',
            barbershop=self.shop_b.id,  # Attempt to assign to Tenant B
            barbershop_id=self.shop_b.id,
        )
        response = self.client.post(self.service_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service = Service.objects.get(id=response.data['id'])
        self.assertEqual(service.barbershop_id, self.shop_a.id)  # Should be Tenant A

    # ========== APPOINTMENT ENDPOINT TESTS ==========

    def test_appointment_crud_isolation(self):
        """Test Appointment CRUD operations for isolation."""
        test_cases = [
            # (actor, target_appointment, expected_status_codes)
            (self.admin_a, 'Admin A', self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.admin_a, 'Admin A', self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_201_CREATED,
             status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
            (self.barber_a, 'Barber A', self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            (self.barber_a, 'Barber A', self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.superuser, 'Superuser', self.appointment_a, 'Appointment A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.appointment_b, 'Appointment B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_201_CREATED,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
        ]

        for actor, actor_desc, target_appointment, target_desc, list_ok, retrieve_ok, create_ok, update_ok, delete_ok in test_cases:
            with self.subTest(actor=actor_desc, target=target_desc):
                self.client.force_authenticate(actor)

                # LIST
                response = self.client.get(self.appointment_list_url)
                self.assertEqual(response.status_code, list_ok,
                               f"Appointment list failed for {actor_desc}")
                if list_ok == status.HTTP_200_OK:
                    ids = [a['id'] for a in response.data['results']]
                    if actor == self.superuser:
                        self.assertIn(target_appointment.id, ids)
                    elif actor.barbershop_id == target_appointment.barbershop_id:
                        self.assertIn(target_appointment.id, ids)
                    else:
                        self.assertNotIn(target_appointment.id, ids)

                # RETRIEVE
                url = self._appointment_detail_url(target_appointment.id)
                response = self.client.get(url)
                self.assertEqual(response.status_code, retrieve_ok,
                               f"Appointment retrieve failed for {actor_desc} -> {target_desc}")

                # CREATE
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN):
                    payload = self._valid_appointment_payload(
                        cliente=self.client_a.pk,
                        barbeiro=self.barber_profile_a.pk,
                        servico=self.service_a.pk,
                    )
                    # Try to force barbershop via foreign keys (should be ignored/validated)
                    payload['barbershop'] = target_appointment.barbershop.id
                    response = self.client.post(self.appointment_list_url, payload, format='json')
                    self.assertEqual(response.status_code, create_ok,
                                   f"Appointment create failed for {actor_desc}")
                    if create_ok == status.HTTP_201_CREATED:
                        appointment = Appointment.objects.get(id=response.data['id'])
                        # Appointment should be in actor's tenant (validated via foreign keys)
                        self.assertEqual(appointment.barbershop_id, actor.barbershop_id)
                        self.assertEqual(appointment.cliente.barbershop_id, actor.barbershop_id)
                        self.assertEqual(appointment.barbeiro.barbershop_id, actor.barbershop_id)
                        self.assertEqual(appointment.servico.barbershop_id, actor.barbershop_id)

                # UPDATE
                if update_ok in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._appointment_detail_url(target_appointment.id)
                    payload = {'observacoes': f'Updated by {actor.nome}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Appointment update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_appointment.refresh_from_db()
                        self.assertEqual(target_appointment.observacoes, f'Updated by {actor.nome}')

                # DELETE
                if delete_ok in (status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    url = self._appointment_detail_url(target_appointment.id)
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_ok,
                                   f"Appointment delete failed for {actor_desc} -> {target_desc}")
                    if delete_ok == status.HTTP_204_NO_CONTENT:
                        target_appointment.refresh_from_db()
                        self.assertEqual(target_appointment.status, Appointment.Status.CANCELADO)

    def test_appointment_cross_tenant_foreign_key_validation(self):
        """Test that creating appointments with cross-tenant foreign keys fails validation."""
        self.client.force_authenticate(self.admin_a)
        # Try to create appointment mixing entities from different tenants
        payload = self._valid_appointment_payload(
            cliente=self.client_b.pk,  # Tenant B client
            barbeiro=self.barber_profile_a.pk,  # Tenant A barber
            servico=self.service_a.pk,  # Tenant A service
        )
        response = self.client.post(self.appointment_list_url, payload, format='json')
        # Should fail because cliente and barbeiro are from different tenants
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that validation error mentions the tenant mismatch
        self.assertTrue(any('barbershop' in str(v).lower() for v in response.data.values()))

    def test_appointment_filter_search_isolation(self):
        """Test that filtering/searching cannot leak data from other tenants."""
        self.client.force_authenticate(self.admin_a)
        # Try to filter by barbershop_id of other tenant
        response = self.client.get(self.appointment_list_url, {'barbershop': self.shop_b.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return empty list or only same-tenant appointments
        ids = [a['id'] for a in response.data['results']]
        self.assertNotIn(self.appointment_b.id, ids)  # Other tenant's appointment
        # May still return same-tenant appointments if they match other filters

    # ========== AUTHENTICATION AND EDGE CASE TESTS ==========

    def test_anonymous_access_denied(self):
        """Test that anonymous users cannot access any endpoints."""
        endpoints = [
            self.user_list_url,
            self.barber_list_url,
            self.service_list_url,
            self.appointment_list_url,
        ]
        for url in endpoints:
            with self.subTest(endpoint=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_barbershop_sees_no_data(self):
        """Test that users without barbershop see empty lists."""
        # Create admin without barbershop
        orphan_admin = User.objects.create_user(
            email='orphan@example.com',
            nome='Orphan Admin',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=None,
        )
        self.client.force_authenticate(orphan_admin)
        endpoints = [
            (self.user_list_url, 'users'),
            (self.barber_list_url, 'barbers'),
            (self.service_list_url, 'services'),
            (self.appointment_list_url, 'appointments'),
        ]
        for url, entity_name in endpoints:
            with self.subTest(entity=entity_name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data['results']), 0,
                               f"Orphan admin saw {entity_name} from other tenants")

    def test_role_based_access_within_same_tenant(self):
        """Test that role-based permissions work correctly within same tenant."""
        # Test that client cannot create services
        self.client.force_authenticate(self.client_a)
        payload = self._valid_service_payload()
        response = self.client.post(self.service_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test that barber cannot create services
        self.client.force_authenticate(self.barber_a)
        response = self.client.post(self.service_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test that admin can create services
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(self.service_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_concurrent_request_isolation(self):
        """Test that concurrent requests don't bleed tenant context."""
        import threading
        results = []

        def make_request(user_entity, expected_shop):
            self.client.force_authenticate(user_entity)
            response = self.client.get(self.service_list_url)
            results.append((user_entity, response.status_code,
                          len(response.data['results']) if response.status_code == 200 else 0))
            self.client.force_authenticate(None)

        # Create threads for different tenants
        threads = [
            threading.Thread(target=make_request, args=(self.admin_a, self.shop_a)),
            threading.Thread(target=make_request, args=(self.admin_b, self.shop_b)),
            threading.Thread(target=make_request, args=(self.client_a, self.shop_a)),
            threading.Thread(target=make_request, args=(self.client_b, self.shop_b)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify each got correct tenant data
        for user_entity, status_code, count in results:
            with self.subTest(user=user_entity.email):
                self.assertEqual(status_code, status.HTTP_200_OK)
                if user_entity.barbershop:
                    # Should see at least their tenant's service
                    self.assertGreaterEqual(count, 1)
                else:
                    # Superuser or orphan should see all or none
                    pass