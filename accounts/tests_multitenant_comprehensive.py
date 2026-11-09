"""
Comprehensive multi-tenant isolation test suite.
Tests all entities, roles, operations, and attack vectors for tenant isolation.
"""
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from appointments.models import Appointment
from datetime import datetime, time, timedelta
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

        # Additional users without barber profiles for testing barber creation
        cls.barber_user_no_profile_a = User.objects.create_user(
            email='barber-no-profile-a@example.com',
            nome='Barber No Profile A',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_a,
        )
        cls.barber_user_no_profile_b = User.objects.create_user(
            email='barber-no-profile-b@example.com',
            nome='Barber No Profile B',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_a,
        )
        cls.barber_user_no_profile_c = User.objects.create_user(
            email='barber-no-profile-c@example.com',
            nome='Barber No Profile C',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_a,
        )
        cls.barber_user_no_profile_d = User.objects.create_user(
            email='barber-no-profile-d@example.com',
            nome='Barber No Profile D',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=cls.shop_b,
        )
        # Barber profiles for UPDATE/DELETE tests (separate from LIST/RETRIEVE fixtures)
        cls.barber_profile_for_update_a = Barber.objects.create(
            user=cls.barber_user_no_profile_c,
            barbershop=cls.shop_a,
            ativo=True,
        )
        cls.barber_profile_for_update_b = Barber.objects.create(
            user=cls.barber_user_no_profile_d,
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
        # Serviços dedicados para o passo de DELETE em test_service_crud_isolation:
        # o DELETE é soft-delete (ativo=False) e ServiceViewSet.get_queryset()
        # filtra por ativo=True por padrão na listagem. Como todos os
        # subTests do método compartilham o mesmo estado (sem rollback entre
        # eles), apagar service_a/service_b em uma iteração faria as
        # iterações seguintes falharem no assert de LIST (o serviço já
        # deletado some da lista). Mesmo padrão de fixtures dedicadas já
        # usado em test_barber_crud_isolation.
        cls.service_for_delete_a = Service.objects.create(
            barbershop=cls.shop_a,
            nome='Service Delete A',
            preco=Decimal('50.00'),
            duracao=30,
            ativo=True,
        )
        cls.service_for_delete_b = Service.objects.create(
            barbershop=cls.shop_b,
            nome='Service Delete B',
            preco=Decimal('60.00'),
            duracao=30,
            ativo=True,
        )

        # Appointments
        # Horário fixo (10:00) dentro do expediente (08:00-18:00) das duas
        # barbearias de teste. `timezone.now() + timedelta(days=1)` preserva
        # a MESMA hora do dia da execução do teste; rodando fora do horário
        # comercial (ex.: à noite), isso cai fora do expediente e qualquer
        # operação que revalide `data_hora` (ex.: um PATCH que só altera
        # 'observacoes', mas passa pelo full_clean() do serializer) falha
        # com 400 de forma não-determinística, dependendo da hora do dia em
        # que a suíte roda.
        future_date = (timezone.localtime() + timedelta(days=1)).date()
        safe_data_hora = timezone.make_aware(datetime.combine(future_date, time(10, 0)))
        cls.appointment_a = Appointment.objects.create(
            barbershop=cls.shop_a,
            cliente=cls.client_a,
            barbeiro=cls.barber_profile_a,
            servico=cls.service_a,
            data_hora=safe_data_hora,
            status=Appointment.Status.AGENDADO,
        )
        cls.appointment_b = Appointment.objects.create(
            barbershop=cls.shop_b,
            cliente=cls.client_b,
            barbeiro=cls.barber_profile_b,
            servico=cls.service_b,
            data_hora=safe_data_hora,
            status=Appointment.Status.AGENDADO,
        )
        # Agendamentos dedicados para UPDATE/DELETE em test_appointment_crud_isolation:
        # O DELETE cancela o agendamento (status -> cancelado). Como todos os
        # subTests compartilham o mesmo estado (sem rollback entre eles),
        # cancelar appointment_a/appointment_b em uma iteração faria as
        # iterações seguintes falharem no UPDATE/RETRIEVE (agendamento já
        # cancelado não permite UPDATE). Mesmo padrão de fixtures dedicadas
        # já usado em test_barber_crud_isolation e test_service_crud_isolation.
        # Usamos dias diferentes (+90, +91, +92, +93) para evitar colisões
        # de horário com o barbeiro.
        for i in range(4):
            future_date = (timezone.localtime() + timedelta(days=90 + i)).date()
            safe_data_hora = timezone.make_aware(datetime.combine(future_date, time(10, 0)))
            if i == 0:
                cls.appointment_for_update_a = Appointment.objects.create(
                    barbershop=cls.shop_a,
                    cliente=cls.client_a,
                    barbeiro=cls.barber_profile_a,
                    servico=cls.service_a,
                    data_hora=safe_data_hora,
                    status=Appointment.Status.AGENDADO,
                )
            elif i == 1:
                cls.appointment_for_update_b = Appointment.objects.create(
                    barbershop=cls.shop_b,
                    cliente=cls.client_b,
                    barbeiro=cls.barber_profile_b,
                    servico=cls.service_b,
                    data_hora=safe_data_hora,
                    status=Appointment.Status.AGENDADO,
                )
            elif i == 2:
                cls.appointment_for_delete_a = Appointment.objects.create(
                    barbershop=cls.shop_a,
                    cliente=cls.client_a,
                    barbeiro=cls.barber_profile_a,
                    servico=cls.service_a,
                    data_hora=safe_data_hora,
                    status=Appointment.Status.AGENDADO,
                )
            else:
                cls.appointment_for_delete_b = Appointment.objects.create(
                    barbershop=cls.shop_b,
                    cliente=cls.client_b,
                    barbeiro=cls.barber_profile_b,
                    servico=cls.service_b,
                    data_hora=safe_data_hora,
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
        # Contador usado por `_valid_appointment_payload` para gerar um
        # horário diferente a cada chamada dentro do mesmo teste, evitando
        # que criações sucessivas no mesmo teste (ex.: em um loop de
        # subTest) colidam com o próprio agendamento criado na chamada
        # anterior (regra real de negócio: um barbeiro não pode ter dois
        # agendamentos sobrepostos).
        self._appointment_payload_offset = 0

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
        # BarberSerializer requires 'user' field - must be a User without existing Barber profile
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
        # Horário fixo (10:00, dentro do expediente 08:00-18:00) em vez de
        # `timezone.now() + timedelta(...)`, que preserva a hora do dia da
        # execução do teste e pode cair fora do expediente dependendo de
        # quando a suíte roda (ver mesmo ajuste em setUpTestData). Cada
        # chamada usa um dia diferente (offset incremental) para não colidir
        # com agendamentos criados por chamadas anteriores no mesmo teste.
        # Start at day 100 to avoid collision with fixtures created on days 90-93
        # (appointment_for_update_a/b, appointment_for_delete_a/b in setUpTestData).
        future_date = (
            timezone.localtime() + timedelta(days=100 + self._appointment_payload_offset)
        ).date()
        self._appointment_payload_offset += 1
        safe_data_hora = timezone.make_aware(datetime.combine(future_date, time(10, 0)))
        payload = {
            'cliente': self.client_a.pk,
            'barbeiro': self.barber_profile_a.pk,
            'servico': self.service_a.pk,
            'data_hora': safe_data_hora.isoformat(),
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
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.barber_a, 'Barber A', self.admin_b, 'Admin B (other tenant)',
             status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.admin_a, 'Admin A (same tenant)',
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN,
             status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            (self.client_a, 'Client A', self.admin_b, 'Admin B (other tenant)',
             status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN,
             status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN),
            # Superuser não pertence a nenhuma barbearia; UserCreateSerializer.create()
            # exige incondicionalmente `request.user.barbershop_id` (ver
            # accounts/serializers.py - regra original, restaurada após
            # remover uma exceção indevida para superuser que havia sido
            # introduzida). Criar usuário fica bloqueado com 400 mesmo para
            # superuser; list/retrieve/update/delete continuam liberados
            # (IsAdminRole permite superuser em qualquer tenant).
            (self.superuser, 'Superuser', self.admin_a, 'Admin A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.admin_b, 'Admin B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
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
                    # Capture original first name before any update to avoid accumulation across subtests
                    original_first_name = target_user.nome.split()[0]
                    payload = {'nome': f'Updated {original_first_name}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_user.refresh_from_db()
                        self.assertEqual(target_user.nome, f'Updated {original_first_name}')

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
        # Superuser cannot create barbers (no barbershop context in BarberViewSet.perform_create)
        # Admin can create barbers in their tenant
        # Barber/Client cannot create barbers (IsAdminRole required)
        # Barber create always creates in actor's tenant regardless of target
        # Use separate fixtures for UPDATE/DELETE to avoid mutating LIST/RETRIEVE fixtures
        test_cases = [
            # (actor, actor_desc, list_target, list_desc, retrieve_target, retrieve_desc, create_ok, update_target, update_desc, delete_target, delete_desc, create_user_attr)
            (self.admin_a, 'Admin A', self.barber_profile_a, 'Barber A (same tenant)',
             self.barber_profile_a, 'Barber A (same tenant)',
             status.HTTP_201_CREATED,
             self.barber_profile_for_update_a, 'Barber Update A (same tenant)',
             self.barber_profile_for_update_a, 'Barber Delete A (same tenant)',
             'barber_user_no_profile_a'),
            (self.admin_a, 'Admin A', self.barber_profile_b, 'Barber B (other tenant)',
             self.barber_profile_b, 'Barber B (other tenant)',
             status.HTTP_201_CREATED,
             self.barber_profile_for_update_b, 'Barber Update B (other tenant)',
             self.barber_profile_for_update_b, 'Barber Delete B (other tenant)',
             'barber_user_no_profile_b'),
            (self.barber_a, 'Barber A', self.barber_profile_a, 'Barber A (same tenant)',
             self.barber_profile_a, 'Barber A (same tenant)',
             status.HTTP_403_FORBIDDEN,
             self.barber_profile_for_update_a, 'Barber Update A (same tenant)',
             self.barber_profile_for_update_a, 'Barber Delete A (same tenant)',
             None),
            (self.barber_a, 'Barber A', self.barber_profile_b, 'Barber B (other tenant)',
             self.barber_profile_b, 'Barber B (other tenant)',
             status.HTTP_403_FORBIDDEN,
             self.barber_profile_for_update_b, 'Barber Update B (other tenant)',
             self.barber_profile_for_update_b, 'Barber Delete B (other tenant)',
             None),
            (self.superuser, 'Superuser', self.barber_profile_a, 'Barber A',
             self.barber_profile_a, 'Barber A',
             status.HTTP_400_BAD_REQUEST,  # Superuser cannot create barbers (no barbershop context)
             self.barber_profile_for_update_a, 'Barber Update A',
             self.barber_profile_for_update_a, 'Barber Delete A',
             None),
            (self.superuser, 'Superuser', self.barber_profile_b, 'Barber B',
             self.barber_profile_b, 'Barber B',
             status.HTTP_400_BAD_REQUEST,  # Superuser cannot create barbers (no barbershop context)
             self.barber_profile_for_update_b, 'Barber Update B',
             self.barber_profile_for_update_b, 'Barber Delete B',
             None),
        ]

        for (actor, actor_desc, list_target, list_desc, retrieve_target, retrieve_desc,
             create_ok, update_target, update_desc, delete_target, delete_desc, create_user_attr) in test_cases:
            with self.subTest(actor=actor_desc, target=list_desc):
                self.client.force_authenticate(actor)

                # LIST
                response = self.client.get(self.barber_list_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                               f"Barber list failed for {actor_desc}")
                ids = [b['id'] for b in response.data['results']]
                if actor == self.superuser:
                    self.assertIn(list_target.id, ids)
                elif actor.barbershop_id == list_target.barbershop_id:
                    self.assertIn(list_target.id, ids)
                else:
                    self.assertNotIn(list_target.id, ids)
                # Also verify no cross-tenant leakage
                if actor != self.superuser and actor.barbershop_id:
                    for barber_data in response.data['results']:
                        self.assertEqual(barber_data['barbershop'], actor.barbershop_id)

                # RETRIEVE
                url = self._barber_detail_url(retrieve_target.id)
                response = self.client.get(url)
                expected_retrieve = status.HTTP_200_OK if (
                    actor == self.superuser or actor.barbershop_id == retrieve_target.barbershop_id
                ) else status.HTTP_404_NOT_FOUND
                self.assertEqual(response.status_code, expected_retrieve,
                               f"Barber retrieve failed for {actor_desc} -> {retrieve_desc}")

                # CREATE
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN):
                    # Use a dedicated user without barber profile for this subTest
                    if create_user_attr:
                        create_user = getattr(self, create_user_attr)
                        payload = self._valid_barber_payload(user=create_user.id)
                    else:
                        payload = self._valid_barber_payload()
                    # Do NOT send barbershop - it's read_only in serializer and forced by view
                    response = self.client.post(self.barber_list_url, payload, format='json')
                    self.assertEqual(response.status_code, create_ok,
                                   f"Barber create failed for {actor_desc}")
                    if create_ok == status.HTTP_201_CREATED:
                        barber = Barber.objects.get(id=response.data['id'])
                        self.assertEqual(barber.barbershop_id, actor.barbershop_id)

                # UPDATE - use separate target to not pollute LIST fixture
                url = self._barber_detail_url(update_target.id)
                # Superuser has IsAdminRole permission and can update any barber across tenants
                expected_update = status.HTTP_200_OK if (actor == self.superuser or (actor == self.admin_a and actor.barbershop_id == update_target.barbershop_id)) else (
                    status.HTTP_404_NOT_FOUND if actor == self.admin_a else status.HTTP_403_FORBIDDEN
                )
                original_ativo = update_target.ativo
                payload = {'ativo': not original_ativo}
                response = self.client.patch(url, payload, format='json')
                self.assertEqual(response.status_code, expected_update,
                               f"Barber update failed for {actor_desc} -> {update_desc}")
                if expected_update == status.HTTP_200_OK:
                    update_target.refresh_from_db()
                    self.assertEqual(update_target.ativo, not original_ativo)

                # DELETE - use separate target
                url = self._barber_detail_url(delete_target.id)
                # Superuser has IsAdminRole permission and can delete any barber across tenants
                expected_delete = status.HTTP_204_NO_CONTENT if (actor == self.superuser or (actor == self.admin_a and actor.barbershop_id == delete_target.barbershop_id)) else (
                    status.HTTP_404_NOT_FOUND if actor == self.admin_a else status.HTTP_403_FORBIDDEN
                )
                response = self.client.delete(url)
                self.assertEqual(response.status_code, expected_delete,
                               f"Barber delete failed for {actor_desc} -> {delete_desc}")

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
            # Superuser não pertence a nenhuma barbearia; ServiceViewSet.perform_create
            # levanta PermissionDenied explicitamente quando barbershop_id é
            # None ("Selecione um contexto de barbearia antes de criar um
            # serviço."), então a criação é sempre barrada com 403 - mesmo
            # princípio já coberto em test_barber_crud_isolation.
            (self.superuser, 'Superuser', self.service_a, 'Service A',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
             status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            (self.superuser, 'Superuser', self.service_b, 'Service B',
             status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
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
                    # Captura o nome original ANTES do update: em iterações
                    # anteriores do loop (mesmo subTest ou anteriores) este
                    # mesmo target_service pode já ter sido renomeado, e usar
                    # `target_service.nome` (já mutado) tanto no payload quanto
                    # na assertion levava a comparações tipo "Updated Updated"
                    # (mesmo bug já corrigido para Users nesta suíte).
                    original_first_name = target_service.nome.split()[0]
                    payload = {'nome': f'Updated {original_first_name}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, update_ok,
                                   f"Service update failed for {actor_desc} -> {target_desc}")
                    if update_ok == status.HTTP_200_OK:
                        target_service.refresh_from_db()
                        self.assertEqual(target_service.nome, f'Updated {original_first_name}')

                # DELETE (soft delete) - usa um serviço dedicado (mesmo tenant
                # do target_service original) para não invalidar o assert de
                # LIST de outras iterações do loop, que ainda esperam
                # target_service ativo e visível.
                if delete_ok in (status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
                    delete_target = (
                        self.service_for_delete_a
                        if target_service.barbershop_id == self.shop_a.id
                        else self.service_for_delete_b
                    )
                    url = self._service_detail_url(delete_target.id)
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_ok,
                                   f"Service delete failed for {actor_desc} -> {target_desc}")
                    if delete_ok == status.HTTP_204_NO_CONTENT:
                        delete_target.refresh_from_db()
                        self.assertFalse(delete_target.ativo)

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
        # Use dedicated fixtures for UPDATE and DELETE to avoid test pollution
        # (same pattern as test_barber_crud_isolation and test_service_crud_isolation)
        test_cases = [
            # (actor, actor_desc, list_target, list_desc, retrieve_target, retrieve_desc,
            #  create_ok, update_target, update_desc, delete_target, delete_desc)
            (self.admin_a, 'Admin A', self.appointment_a, 'Appointment A (same tenant)',
             self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_a, 'Appointment Update A (same tenant)',
             self.appointment_for_delete_a, 'Appointment Delete A (same tenant)'),
            (self.admin_a, 'Admin A', self.appointment_b, 'Appointment B (other tenant)',
             self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_b, 'Appointment Update B (other tenant)',
             self.appointment_for_delete_b, 'Appointment Delete B (other tenant)'),
            # Barbeiro pode criar agendamento (para a própria agenda) e
            # cliente pode criar o próprio agendamento - ver
            # DOCUMENTACAO_API.md ("POST /appointments/ | Autenticado, dentro
            # do escopo do perfil") e AppointmentViewSet.perform_create, que
            # trata explicitamente os casos is_cliente/is_barbeiro. Não há
            # nenhuma restrição de permissão de 'create' para estes papéis
            # (diferente de Service/Barber, que exigem IsAdminRole).
            (self.barber_a, 'Barber A', self.appointment_a, 'Appointment A (same tenant)',
             self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_a, 'Appointment Update A (same tenant)',
             self.appointment_for_delete_a, 'Appointment Delete A (same tenant)'),
            # UPDATE em appointment_b: get_permissions libera (IsAdminOrBarberRole
            # só checa papel, não objeto), mas o queryset de barbeiro é
            # filtrado a `barbeiro=perfil_barbeiro` (AppointmentViewSet.get_queryset)
            # - appointment_b pertence a barber_profile_b, então get_object()
            # não encontra -> 404 (não 403). DELETE continua 403 porque a
            # permissão de destroy para barbeiro exige IsAdminRole, negada
            # antes de qualquer consulta ao objeto.
            (self.barber_a, 'Barber A', self.appointment_b, 'Appointment B (other tenant)',
             self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_b, 'Appointment Update B (other tenant)',
             self.appointment_for_delete_b, 'Appointment Delete B (other tenant)'),
            # DELETE para cliente é permitido (cancelamento do próprio
            # agendamento - AppointmentViewSet.get_permissions/perform_destroy);
            # appointment_a.cliente é client_a, então o próprio agendamento
            # pode ser cancelado -> 204.
            (self.client_a, 'Client A', self.appointment_a, 'Appointment A (same tenant)',
             self.appointment_a, 'Appointment A (same tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_a, 'Appointment Update A (same tenant)',
             self.appointment_for_delete_a, 'Appointment Delete A (same tenant)'),
            # appointment_b pertence a client_b: fora do queryset do cliente
            # (filtrado por `cliente=user`) -> 404 tanto para UPDATE quanto
            # para DELETE (a permissão em si não bloqueia o cliente, quem
            # bloqueia é o queryset).
            (self.client_a, 'Client A', self.appointment_b, 'Appointment B (other tenant)',
             self.appointment_b, 'Appointment B (other tenant)',
             status.HTTP_201_CREATED,
             self.appointment_for_update_b, 'Appointment Update B (other tenant)',
             self.appointment_for_delete_b, 'Appointment Delete B (other tenant)'),
            # Superuser não pertence a nenhuma barbearia (barbershop_id=None).
            # AppointmentSerializer.validate() monta uma cópia em memória do
            # Appointment com barbershop_id=None e chama full_clean(); como
            # Appointment.barbershop não é nullable, isso é barrado com 400
            # (campo obrigatório) antes mesmo de perform_create's guard
            # (PermissionDenied) rodar - diferente de Service/Barber, cujos
            # perform_create levantam 403 diretamente. Ver também o mesmo
            # princípio (superuser sem tenant não cria recurso de tenant) já
            # coberto em test_service_crud_isolation/test_barber_crud_isolation.
            (self.superuser, 'Superuser', self.appointment_a, 'Appointment A',
             self.appointment_a, 'Appointment A',
             status.HTTP_400_BAD_REQUEST,
             self.appointment_for_update_a, 'Appointment Update A',
             self.appointment_for_delete_a, 'Appointment Delete A'),
            (self.superuser, 'Superuser', self.appointment_b, 'Appointment B',
             self.appointment_b, 'Appointment B',
             status.HTTP_400_BAD_REQUEST,
             self.appointment_for_update_b, 'Appointment Update B',
             self.appointment_for_delete_b, 'Appointment Delete B'),
        ]

        for (actor, actor_desc, list_target, list_desc, retrieve_target, retrieve_desc,
             create_ok, update_target, update_desc, delete_target, delete_desc) in test_cases:
            with self.subTest(actor=actor_desc, target=list_desc):
                self.client.force_authenticate(actor)

                # LIST
                response = self.client.get(self.appointment_list_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                               f"Appointment list failed for {actor_desc}")
                ids = [a['id'] for a in response.data['results']]
                if actor == self.superuser:
                    self.assertIn(list_target.id, ids)
                elif actor.barbershop_id == list_target.barbershop_id:
                    self.assertIn(list_target.id, ids)
                else:
                    self.assertNotIn(list_target.id, ids)

                # RETRIEVE
                url = self._appointment_detail_url(retrieve_target.id)
                response = self.client.get(url)
                expected_retrieve = status.HTTP_200_OK if (
                    actor == self.superuser or actor.barbershop_id == retrieve_target.barbershop_id
                ) else status.HTTP_404_NOT_FOUND
                self.assertEqual(response.status_code, expected_retrieve,
                               f"Appointment retrieve failed for {actor_desc} -> {retrieve_desc}")

                # CREATE
                if create_ok in (status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST):
                    payload = self._valid_appointment_payload(
                        cliente=self.client_a.pk,
                        barbeiro=self.barber_profile_a.pk,
                        servico=self.service_a.pk,
                    )
                    # barbershop is read-only and set by the view from request.user.barbershop_id;
                    # do not include it in the payload to avoid serializer validation against it.
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

                # UPDATE - use separate target to not pollute LIST/RETRIEVE fixtures
                # Superuser can update any appointment across tenants
                # Admin can update same-tenant appointments
                # Barber can update same-tenant appointments where they are the barber (queryset filtered)
                # Client can update their own same-tenant appointments
                # Cross-tenant: Admin gets 404, Barber gets 404 (queryset), Client gets 404 (queryset)
                if update_target:
                    url = self._appointment_detail_url(update_target.id)
                    # Determine expected status based on actor and target relationship
                    if actor == self.superuser:
                        expected_update = status.HTTP_200_OK
                    elif actor == self.admin_a:
                        expected_update = status.HTTP_200_OK if actor.barbershop_id == update_target.barbershop_id else status.HTTP_404_NOT_FOUND
                    elif actor == self.barber_a:
                        # Barber can update if appointment is in same tenant AND they are the barber
                        expected_update = status.HTTP_200_OK if (actor.barbershop_id == update_target.barbershop_id and update_target.barbeiro.user_id == actor.id) else status.HTTP_404_NOT_FOUND
                    elif actor == self.client_a:
                        # Client can update if appointment is in same tenant AND they are the client
                        expected_update = status.HTTP_200_OK if (actor.barbershop_id == update_target.barbershop_id and update_target.cliente_id == actor.id) else status.HTTP_404_NOT_FOUND
                    else:
                        expected_update = status.HTTP_404_NOT_FOUND

                    payload = {'observacoes': f'Updated by {actor.nome}'}
                    response = self.client.patch(url, payload, format='json')
                    self.assertEqual(response.status_code, expected_update,
                                   f"Appointment update failed for {actor_desc} -> {update_desc}")
                    if expected_update == status.HTTP_200_OK:
                        update_target.refresh_from_db()
                        self.assertEqual(update_target.observacoes, f'Updated by {actor.nome}')

                # DELETE - use separate target
                # Superuser can delete any appointment across tenants
                # Admin can delete same-tenant appointments
                # Barber cannot delete (requires IsAdminRole)
                # Client can delete their own same-tenant appointments (cancel)
                if delete_target:
                    url = self._appointment_detail_url(delete_target.id)
                    if actor == self.superuser:
                        expected_delete = status.HTTP_204_NO_CONTENT
                    elif actor == self.admin_a:
                        expected_delete = status.HTTP_204_NO_CONTENT if actor.barbershop_id == delete_target.barbershop_id else status.HTTP_404_NOT_FOUND
                    elif actor == self.barber_a:
                        expected_delete = status.HTTP_403_FORBIDDEN
                    elif actor == self.client_a:
                        expected_delete = status.HTTP_204_NO_CONTENT if (actor.barbershop_id == delete_target.barbershop_id and delete_target.cliente_id == actor.id) else status.HTTP_404_NOT_FOUND
                    else:
                        expected_delete = status.HTTP_404_NOT_FOUND

                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, expected_delete,
                                   f"Appointment delete failed for {actor_desc} -> {delete_desc}")
                    if expected_delete == status.HTTP_204_NO_CONTENT:
                        delete_target.refresh_from_db()
                        self.assertEqual(delete_target.status, Appointment.Status.CANCELADO)

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
        # Check that validation error mentions the tenant mismatch. As mensagens
        # reais (AppointmentSerializer.validate/Appointment.clean) são em
        # português e usam "barbearia", não a palavra em inglês "barbershop".
        self.assertTrue(any('barbearia' in str(v).lower() for v in response.data.values()))

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


class ConcurrentTenantIsolationTests(TransactionTestCase):
    """Isolamento de tenant sob requisições realmente concorrentes.

    Usa TransactionTestCase (dados commitados de verdade) porque threads
    abrem conexões próprias com o banco e, dentro de um TestCase comum, não
    enxergam os dados criados na transação do teste (o que fazia a versão
    anterior deste teste receber listas vazias - 0 serviços - mesmo com a
    aplicação correta). Cada thread usa seu próprio APIClient e fecha sua
    conexão ao terminar.
    """

    def setUp(self):
        self.shop_a = Barbershop.objects.create(
            nome='Concurrent Shop A', endereco='Rua A', telefone='11999990001',
            email='conc-a@example.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        self.shop_b = Barbershop.objects.create(
            nome='Concurrent Shop B', endereco='Rua B', telefone='11999990002',
            email='conc-b@example.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        self.admin_a = User.objects.create_user(
            email='conc-admin-a@example.com', nome='Admin A', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=self.shop_a,
        )
        self.admin_b = User.objects.create_user(
            email='conc-admin-b@example.com', nome='Admin B', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=self.shop_b,
        )
        self.client_a = User.objects.create_user(
            email='conc-client-a@example.com', nome='Client A', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=self.shop_a,
        )
        self.client_b = User.objects.create_user(
            email='conc-client-b@example.com', nome='Client B', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=self.shop_b,
        )
        self.service_a = Service.objects.create(
            barbershop=self.shop_a, nome='Service A', preco=Decimal('50.00'), duracao=30, ativo=True,
        )
        self.service_b = Service.objects.create(
            barbershop=self.shop_b, nome='Service B', preco=Decimal('60.00'), duracao=30, ativo=True,
        )
        self.service_list_url = reverse('service-list')

    def test_concurrent_request_isolation(self):
        """Test that concurrent requests don't bleed tenant context."""
        import threading
        from django.db import connections

        results = []
        errors = []
        barrier = threading.Barrier(4)

        def make_request(user_entity):
            try:
                thread_client = APIClient()
                thread_client.force_authenticate(user_entity)
                barrier.wait(timeout=10)  # dispara as 4 requisições ao mesmo tempo
                response = thread_client.get(self.service_list_url)
                ids = (
                    {s['id'] for s in response.data['results']}
                    if response.status_code == 200 else set()
                )
                results.append((user_entity, response.status_code, ids))
            except Exception as exc:  # noqa: BLE001 - reportado abaixo
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=make_request, args=(u,))
            for u in (self.admin_a, self.admin_b, self.client_a, self.client_b)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 4)

        # Cada usuário vê exatamente os serviços da PRÓPRIA barbearia.
        expected = {
            self.shop_a.id: {self.service_a.id},
            self.shop_b.id: {self.service_b.id},
        }
        for user_entity, status_code, ids in results:
            with self.subTest(user=user_entity.email):
                self.assertEqual(status_code, status.HTTP_200_OK)
                self.assertEqual(ids, expected[user_entity.barbershop_id])
