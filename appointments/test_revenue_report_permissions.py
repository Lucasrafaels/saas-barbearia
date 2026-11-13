"""
SEC-02 — o relatório de faturamento é restrito a administradores.

`GET /api/v1/appointments/revenue-report/` expõe o faturamento total da
barbearia, por barbeiro, por serviço e por dia. Somente o perfil `admin`
(ou o superusuário da plataforma) pode consultá-lo, e sempre limitado à
própria barbearia. A regra é aplicada no backend, independentemente do
que o frontend mostra.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment

URL = reverse('appointment-revenue-report')
FINANCIAL_FIELDS = ('total_revenue', 'total_appointments', 'by_barber', 'by_service', 'daily')


class RevenueReportPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.shop_a, cls.users_a, cls.barber_a, cls.service_a = cls._create_tenant('a', Decimal('50.00'))
        cls.shop_b, cls.users_b, cls.barber_b, cls.service_b = cls._create_tenant('b', Decimal('80.00'))

        # Dois atendimentos realizados na barbearia A (total 100.00) e três
        # na barbearia B (total 240.00), todos dentro do período consultado.
        cls.day = timezone.localdate() - timedelta(days=2)
        cls._create_done_appointments(cls.shop_a, cls.users_a, cls.barber_a, cls.service_a, count=2)
        cls._create_done_appointments(cls.shop_b, cls.users_b, cls.barber_b, cls.service_b, count=3)

        cls.params = {
            'start': (cls.day - timedelta(days=1)).isoformat(),
            'end': timezone.localdate().isoformat(),
        }

    @classmethod
    def _create_tenant(cls, suffix, price):
        shop = Barbershop.objects.create(
            nome=f'Barbearia {suffix.upper()}',
            endereco='Rua Teste, 1',
            telefone='11999999999',
            email=f'loja-{suffix}@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        users = {
            perfil: User.objects.create_user(
                email=f'{perfil}-{suffix}@example.com',
                nome=f'{perfil.title()} {suffix.upper()}',
                password='Senha-segura-123',
                tipo_perfil=perfil,
                barbershop=shop,
            )
            for perfil in (User.TipoPerfil.ADMIN, User.TipoPerfil.BARBEIRO, User.TipoPerfil.CLIENTE)
        }
        barber = Barber.objects.create(user=users[User.TipoPerfil.BARBEIRO], barbershop=shop)
        service = Service.objects.create(barbershop=shop, nome=f'Corte {suffix.upper()}', preco=price, duracao=30)
        return shop, users, barber, service

    @classmethod
    def _create_done_appointments(cls, shop, users, barber, service, count):
        for i in range(count):
            Appointment.objects.create(
                barbershop=shop,
                cliente=users[User.TipoPerfil.CLIENTE],
                barbeiro=barber,
                servico=service,
                data_hora=timezone.make_aware(datetime.combine(cls.day, time(9 + i))),
                status=Appointment.Status.REALIZADO,
                preco_historico=service.preco,
            )

    def _authenticate_with_jwt(self, user):
        """Autentica com um access token real, passando pela JWTAuthentication."""
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def assert_no_financial_data(self, response):
        for field in FINANCIAL_FIELDS:
            self.assertNotIn(field, response.data)

    # 1. Administrador autorizado consegue consultar ---------------------------

    def test_admin_consulta_o_faturamento_da_propria_barbearia(self):
        self._authenticate_with_jwt(self.users_a[User.TipoPerfil.ADMIN])

        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Decimal: o SQLite devolve '100' e o PostgreSQL, '100.00'.
        self.assertEqual(Decimal(response.data['total_revenue']), Decimal('100.00'))
        self.assertEqual(response.data['total_appointments'], 2)
        [por_barbeiro] = response.data['by_barber']
        self.assertEqual(por_barbeiro['barbeiro'], 'Barbeiro A')
        self.assertEqual(Decimal(por_barbeiro['revenue']), Decimal('100.00'))
        self.assertEqual(por_barbeiro['count'], 2)

    # 2. Cliente recebe acesso negado -----------------------------------------

    def test_cliente_recebe_403_sem_dados_financeiros(self):
        self._authenticate_with_jwt(self.users_a[User.TipoPerfil.CLIENTE])

        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_financial_data(response)

    # 3. Barbeiro recebe acesso negado ----------------------------------------

    def test_barbeiro_recebe_403_sem_dados_financeiros(self):
        self._authenticate_with_jwt(self.users_a[User.TipoPerfil.BARBEIRO])

        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_financial_data(response)

    def test_barbeiro_nao_contorna_a_restricao_filtrando_pelo_proprio_id(self):
        self._authenticate_with_jwt(self.users_a[User.TipoPerfil.BARBEIRO])

        response = self.client.get(URL, {**self.params, 'barbeiro': self.barber_a.pk})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_financial_data(response)

    # 4. Usuário não autenticado não consegue consultar -----------------------

    def test_usuario_nao_autenticado_recebe_401(self):
        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_no_financial_data(response)

    def test_token_invalido_recebe_401(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-invalido')

        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_no_financial_data(response)

    # 5. Administrador não acessa dados de outra barbearia --------------------

    def test_admin_nao_ve_faturamento_de_outra_barbearia(self):
        self._authenticate_with_jwt(self.users_b[User.TipoPerfil.ADMIN])

        response = self.client.get(URL, self.params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['total_revenue']), Decimal('240.00'))
        self.assertEqual(response.data['total_appointments'], 3)
        nomes = {item['barbeiro'] for item in response.data['by_barber']}
        self.assertEqual(nomes, {'Barbeiro B'})
        self.assertNotIn('Corte A', {item['servico'] for item in response.data['by_service']})

    def test_admin_nao_obtem_dados_de_outra_barbearia_pelo_filtro_de_barbeiro(self):
        self._authenticate_with_jwt(self.users_a[User.TipoPerfil.ADMIN])

        response = self.client.get(URL, {**self.params, 'barbeiro': self.barber_b.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['total_revenue']), Decimal('0'))
        self.assertEqual(response.data['total_appointments'], 0)
        self.assertEqual(response.data['by_barber'], [])
        self.assertEqual(response.data['by_service'], [])
        self.assertEqual(response.data['daily'], [])


class AdminFeaturesAfterRevenueRestrictionTests(APITestCase):
    """6. A restrição do relatório não afeta as demais funcionalidades."""

    @classmethod
    def setUpTestData(cls):
        cls.shop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        cls.admin = User.objects.create_user(
            email='admin@example.com', nome='Admin', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=cls.shop,
        )
        cls.client_user = User.objects.create_user(
            email='cliente@example.com', nome='Cliente', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=cls.shop,
        )
        barber_user = User.objects.create_user(
            email='barbeiro@example.com', nome='Barbeiro', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=cls.shop,
        )
        cls.barber = Barber.objects.create(user=barber_user, barbershop=cls.shop)
        cls.service = Service.objects.create(barbershop=cls.shop, nome='Corte', preco='50.00', duracao=30)

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def _future_slot(self, days=1, hour=10):
        return timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=days), time(hour)))

    def test_admin_cria_lista_confirma_e_cancela_agendamento(self):
        create = self.client.post(reverse('appointment-list'), {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': self._future_slot().isoformat(),
        }, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        detail_url = reverse('appointment-detail', args=[create.data['id']])

        listing = self.client.get(reverse('appointment-list'))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data['count'], 1)

        confirm = self.client.patch(detail_url, {'status': Appointment.Status.CONFIRMADO}, format='json')
        self.assertEqual(confirm.status_code, status.HTTP_200_OK, confirm.data)

        cancel = self.client.delete(detail_url)
        self.assertEqual(cancel.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_consulta_horarios_disponiveis(self):
        response = self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data': (timezone.localdate() + timedelta(days=1)).isoformat(),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('10:00', response.data['slots'])

    def test_admin_gerencia_servicos_e_usuarios(self):
        service = self.client.post(reverse('service-list'), {
            'nome': 'Barba', 'preco': '30.00', 'duracao': 30,
        }, format='json')
        self.assertEqual(service.status_code, status.HTTP_201_CREATED, service.data)

        users = self.client.get(reverse('user-list'))
        self.assertEqual(users.status_code, status.HTTP_200_OK)

    def test_cliente_continua_agendando_e_listando_os_proprios_horarios(self):
        self.client.force_authenticate(self.client_user)

        create = self.client.post(reverse('appointment-list'), {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': self._future_slot(hour=11).isoformat(),
        }, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)

        listing = self.client.get(reverse('appointment-list'))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data['count'], 1)
