"""Ataques de API contra IDs de outro tenant devem falhar no backend."""
from datetime import time, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment


class MultiTenantIsolationTests(APITestCase):
    """Cobre leitura, criação, edição e remoção nas duas barbearias."""

    def setUp(self):
        self.shop_a = self.create_shop('Barbearia A', 'a@example.com')
        self.shop_b = self.create_shop('Barbearia B', 'b@example.com')

        self.admin_a = self.create_user('admin-a@example.com', 'admin', self.shop_a)
        # O staff continua limitado ao tenant pela queryset do endpoint.
        self.admin_a.is_staff = True
        self.admin_a.save(update_fields=['is_staff'])
        self.client_a = self.create_user('client-a@example.com', 'cliente', self.shop_a)
        self.barber_user_a = self.create_user('barber-a@example.com', 'barbeiro', self.shop_a)
        self.barber_a = Barber.objects.create(user=self.barber_user_a, barbershop=self.shop_a)
        self.service_a = Service.objects.create(
            barbershop=self.shop_a, nome='Corte A', preco='50.00', duracao=30,
        )

        self.admin_b = self.create_user('admin-b@example.com', 'admin', self.shop_b)
        self.client_b = self.create_user('client-b@example.com', 'cliente', self.shop_b)
        self.barber_user_b = self.create_user('barber-b@example.com', 'barbeiro', self.shop_b)
        self.barber_b = Barber.objects.create(user=self.barber_user_b, barbershop=self.shop_b)
        self.service_b = Service.objects.create(
            barbershop=self.shop_b, nome='Corte B', preco='60.00', duracao=30,
        )

        self.start = (timezone.localtime() + timedelta(days=2)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        self.appointment_a = Appointment.objects.create(
            barbershop=self.shop_a,
            cliente=self.client_a,
            barbeiro=self.barber_a,
            servico=self.service_a,
            data_hora=self.start,
        )
        self.appointment_b = Appointment.objects.create(
            barbershop=self.shop_b,
            cliente=self.client_b,
            barbeiro=self.barber_b,
            servico=self.service_b,
            data_hora=self.start,
        )
        self.client.force_authenticate(self.admin_a)

    @staticmethod
    def create_shop(name, email):
        return Barbershop.objects.create(
            nome=name,
            endereco='Rua dos Testes, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )

    @staticmethod
    def create_user(email, profile, shop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=profile,
            barbershop=shop,
        )

    def appointment_payload(self, **overrides):
        payload = {
            'cliente': self.client_a.pk,
            'barbeiro': self.barber_a.pk,
            'servico': self.service_a.pk,
            'data_hora': (self.start + timedelta(minutes=60)).isoformat(),
        }
        payload.update(overrides)
        return payload

    def test_listagens_nao_expoem_registros_de_outro_tenant(self):
        endpoints = (
            ('user-list', self.admin_b.pk),
            ('barbershop-list', self.shop_b.pk),
            ('barber-list', self.barber_b.pk),
            ('service-list', self.service_b.pk),
            ('appointment-list', self.appointment_b.pk),
        )
        for route, forbidden_id in endpoints:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertNotIn(forbidden_id, [row['id'] for row in response.data['results']])

    def test_ids_de_outro_tenant_retornao_404_em_leitura_edicao_e_exclusao(self):
        targets = (
            ('user-detail', self.admin_b.pk, {'nome': 'Ataque'}),
            ('barbershop-detail', self.shop_b.pk, {'nome': 'Ataque'}),
            ('barber-detail', self.barber_b.pk, {'especialidade': 'Ataque'}),
            ('service-detail', self.service_b.pk, {'nome': 'Ataque'}),
            ('appointment-detail', self.appointment_b.pk, {'observacoes': 'Ataque'}),
        )
        for route, object_id, payload in targets:
            url = reverse(route, args=[object_id])
            with self.subTest(route=route, operation='get'):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
            with self.subTest(route=route, operation='patch'):
                self.assertEqual(
                    self.client.patch(url, payload, format='json').status_code,
                    status.HTTP_404_NOT_FOUND,
                )
            with self.subTest(route=route, operation='delete'):
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_relacionamentos_de_outro_tenant_sao_rejeitados_no_agendamento(self):
        attacks = (
            ('cliente', self.client_b.pk),
            ('barbeiro', self.barber_b.pk),
            ('servico', self.service_b.pk),
        )
        for field, foreign_id in attacks:
            with self.subTest(field=field):
                response = self.client.post(
                    reverse('appointment-list'),
                    self.appointment_payload(**{field: foreign_id}),
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertEqual(Appointment.objects.filter(barbershop=self.shop_a).count(), 1)

    def test_campos_de_tenant_e_ids_forjados_nao_substituem_o_tenant_servidor(self):
        response = self.client.post(
            reverse('appointment-list'),
            self.appointment_payload(
                barbershop=self.shop_b.pk,
                barbershop_id=self.shop_b.pk,
                tenant_id=self.shop_b.pk,
                barber_id=self.barber_b.pk,
                service_id=self.service_b.pk,
                appointment_id=self.appointment_b.pk,
                user_id=self.client_b.pk,
            ),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get(pk=response.data['id'])
        self.assertEqual(appointment.barbershop_id, self.shop_a.pk)
        self.assertEqual(appointment.cliente_id, self.client_a.pk)
        self.assertEqual(appointment.barbeiro_id, self.barber_a.pk)
        self.assertEqual(appointment.servico_id, self.service_a.pk)

    def test_criacao_de_usuarios_barbeiros_e_servicos_ignora_tenant_informado(self):
        user_response = self.client.post(
            reverse('user-list'),
            {
                'email': 'new-client@example.com',
                'nome': 'New client',
                'password': 'Senha-segura-123',
                'tipo_perfil': 'cliente',
                'barbershop': self.shop_b.pk,
                'barbershop_id': self.shop_b.pk,
                'tenant_id': self.shop_b.pk,
                'user_id': self.client_b.pk,
            },
            format='json',
        )
        self.assertEqual(user_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(pk=user_response.data['id']).barbershop_id, self.shop_a.pk)

        new_barber_user = self.create_user('new-barber@example.com', 'barbeiro', self.shop_a)
        barber_response = self.client.post(
            reverse('barber-list'),
            {
                'user': new_barber_user.pk,
                'barbershop': self.shop_b.pk,
                'barbershop_id': self.shop_b.pk,
                'tenant_id': self.shop_b.pk,
                'user_id': self.barber_user_b.pk,
            },
            format='json',
        )
        self.assertEqual(barber_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Barber.objects.get(pk=barber_response.data['id']).barbershop_id, self.shop_a.pk)

        service_response = self.client.post(
            reverse('service-list'),
            {
                'nome': 'Serviço seguro',
                'preco': '35.00',
                'duracao': 30,
                'barbershop': self.shop_b.pk,
                'barbershop_id': self.shop_b.pk,
                'tenant_id': self.shop_b.pk,
                'service_id': self.service_b.pk,
            },
            format='json',
        )
        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Service.objects.get(pk=service_response.data['id']).barbershop_id, self.shop_a.pk)

    def test_atualizacao_nao_pode_reapontar_relacionamentos_ou_tenant(self):
        response = self.client.patch(
            reverse('appointment-detail', args=[self.appointment_a.pk]),
            {
                'cliente': self.client_b.pk,
                'barbeiro': self.barber_b.pk,
                'servico': self.service_b.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.appointment_a.refresh_from_db()
        self.assertEqual(self.appointment_a.barbershop_id, self.shop_a.pk)
        self.assertEqual(self.appointment_a.cliente_id, self.client_a.pk)
        self.assertEqual(self.appointment_a.barbeiro_id, self.barber_a.pk)
        self.assertEqual(self.appointment_a.servico_id, self.service_a.pk)

        response = self.client.patch(
            reverse('user-detail', args=[self.client_a.pk]),
            {'barbershop': self.shop_b.pk, 'barbershop_id': self.shop_b.pk, 'tenant_id': self.shop_b.pk},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_a.refresh_from_db()
        self.assertEqual(self.client_a.barbershop_id, self.shop_a.pk)

    def test_available_slots_nao_revela_barbeiro_ou_servico_de_outro_tenant(self):
        response = self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': self.barber_b.pk,
            'servico': self.service_a.pk,
            'data': self.start.date().isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': self.barber_a.pk,
            'servico': self.service_b.pk,
            'data': self.start.date().isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filtros_com_ids_de_outro_tenant_nao_contornam_a_queryset(self):
        """Filtros são aplicados depois do escopo do tenant, nunca antes."""
        # TEN-01/SEC-10: as opções dos filtros de agendamento vêm da barbearia
        # do usuário. O ID de outra barbearia recebe a mesma recusa (400) de um
        # ID inexistente; antes recebia 200 com lista vazia, o que revelava que
        # ele existia.
        for params in ({'barbeiro': self.barber_b.pk}, {'servico': self.service_b.pk}):
            with self.subTest(url=reverse('appointment-list'), params=params):
                response = self.client.get(reverse('appointment-list'), params)
                inexistente = self.client.get(reverse('appointment-list'), {campo: 999999 for campo in params})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data, inexistente.data)
                self.assertNotIn('results', response.data)
        endpoints = (
            (reverse('barber-list'), {'ativo': 'true'}),
            (reverse('service-list'), {'ativo': 'true'}),
        )
        for url, params in endpoints:
            with self.subTest(url=url, params=params):
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertNotIn(
                    self.appointment_b.pk,
                    [item['id'] for item in response.data['results']],
                )

    def test_admin_cliente_e_barbeiro_nao_alteram_objeto_de_outro_tenant_por_get_put_patch_delete(self):
        """Cobertura de todos os verbos em objetos de tenant B por atores de A."""
        actors = (self.admin_a, self.client_a, self.barber_user_a)
        targets = (
            ('user-detail', self.admin_b.pk, {'nome': 'Ataque'}),
            ('barbershop-detail', self.shop_b.pk, {'nome': 'Ataque'}),
            ('barber-detail', self.barber_b.pk, {'especialidade': 'Ataque'}),
            ('service-detail', self.service_b.pk, {'nome': 'Ataque'}),
            ('appointment-detail', self.appointment_b.pk, {'observacoes': 'Ataque'}),
        )
        for actor in actors:
            self.client.force_authenticate(actor)
            for route, object_id, payload in targets:
                url = reverse(route, args=[object_id])
                for method in ('get', 'put', 'patch', 'delete'):
                    with self.subTest(actor=actor.tipo_perfil, route=route, method=method):
                        response = getattr(self.client, method)(
                            url, payload if method in ('put', 'patch') else None,
                            format='json' if method in ('put', 'patch') else None,
                        )
                        # Algumas ações bloqueiam pela permissão antes da
                        # busca do objeto (403); as demais retornam 404.
                        self.assertIn(response.status_code, (
                            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
                        ))

        self.admin_b.refresh_from_db()
        self.barber_b.refresh_from_db()
        self.service_b.refresh_from_db()
        self.appointment_b.refresh_from_db()
        self.assertEqual(self.admin_b.nome, 'admin-b')
        self.assertNotEqual(self.barber_b.especialidade, 'Ataque')
        self.assertNotEqual(self.service_b.nome, 'Ataque')
        self.assertNotEqual(self.appointment_b.observacoes, 'Ataque')

    def test_superuser_eh_excecao_global_explicita_e_nao_um_papel_de_tenant(self):
        """Superuser é operador da plataforma; admin comum continua isolado."""
        superuser = User.objects.create_superuser(
            email='root@example.com', nome='Root', password='Senha-segura-123',
        )
        self.client.force_authenticate(superuser)
        self.assertEqual(
            self.client.get(reverse('user-detail', args=[self.admin_b.pk])).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(reverse('barbershop-detail', args=[self.shop_b.pk])).status_code,
            status.HTTP_200_OK,
        )
        for route, object_id in (
            ('barber-detail', self.barber_b.pk),
            ('service-detail', self.service_b.pk),
            ('appointment-detail', self.appointment_b.pk),
        ):
            with self.subTest(route=route):
                self.assertEqual(
                    self.client.get(reverse(route, args=[object_id])).status_code,
                    status.HTTP_200_OK,
                )

    def test_admin_sem_tenant_nao_lista_usuarios_orfaos(self):
        admin_sem_tenant = User.objects.create_user(
            email='orphan-admin@example.com', nome='Orphan admin',
            password='Senha-segura-123', tipo_perfil='admin',
        )
        self.client.force_authenticate(admin_sem_tenant)
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])
