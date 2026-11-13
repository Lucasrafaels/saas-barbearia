"""
BUS-01 — a barbearia nunca fica sem administrador ativo.

Um admin não pode rebaixar nem desativar a própria conta, e nenhuma
operação da API pode rebaixar ou desativar o último admin ativo de uma
barbearia, nem mesmo duas operações simultâneas. O gerenciamento dos
demais usuários continua liberado.
"""
import threading
from datetime import time
from unittest import mock, skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from accounts.views import UserViewSet
from barbershops.models import Barber, Barbershop

PASSWORD = 'Senha-segura-123'


def create_barbershop(nome='Barbearia Central'):
    return Barbershop.objects.create(
        nome=nome,
        endereco='Rua Principal, 100',
        telefone='11999999999',
        email=f'{nome.split()[-1].lower()}@example.com',
        horario_abertura=time(8),
        horario_fechamento=time(18),
    )


def create_user(email, perfil, barbershop, **extra):
    return User.objects.create_user(
        email=email, nome=email.split('@')[0].title(), password=PASSWORD,
        tipo_perfil=perfil, barbershop=barbershop, **extra,
    )


def detail_url(user):
    return reverse('user-detail', args=[user.pk])


class AdminProtectionTests(APITestCase):
    def setUp(self):
        self.shop = create_barbershop()
        self.admin = create_user('admin@example.com', User.TipoPerfil.ADMIN, self.shop)
        self.client_user = create_user('cliente@example.com', User.TipoPerfil.CLIENTE, self.shop)
        barber_user = create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO, self.shop)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.shop)
        self.superuser = User.objects.create_superuser(
            email='plataforma@example.com', nome='Plataforma', password=PASSWORD,
        )
        self.client.force_authenticate(self.admin)

    def add_second_admin(self, **extra):
        return create_user('admin2@example.com', User.TipoPerfil.ADMIN, self.shop, **extra)

    def assert_still_active_admin(self, user):
        user.refresh_from_db()
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.ADMIN)
        self.assertTrue(user.is_active)

    # Admin tentando rebaixar a própria conta ---------------------------------

    def test_admin_nao_rebaixa_a_propria_conta(self):
        for perfil in (User.TipoPerfil.CLIENTE, User.TipoPerfil.BARBEIRO):
            response = self.client.patch(detail_url(self.admin), {'tipo_perfil': perfil}, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, perfil)
            self.assert_still_active_admin(self.admin)

        # O acesso administrativo continua funcionando.
        response = self.client.post(reverse('user-list'), {
            'email': 'novo@example.com', 'nome': 'Novo', 'password': PASSWORD,
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_nao_se_rebaixa_nem_havendo_outro_admin(self):
        self.add_second_admin()

        response = self.client.patch(detail_url(self.admin), {'tipo_perfil': User.TipoPerfil.CLIENTE}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('próprio perfil', str(response.data['tipo_perfil']))
        self.assert_still_active_admin(self.admin)

    # Admin tentando desativar a própria conta --------------------------------

    def test_admin_nao_desativa_a_propria_conta_por_patch(self):
        response = self.client.patch(detail_url(self.admin), {'is_active': False}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('própria conta', str(response.data['is_active']))
        self.assert_still_active_admin(self.admin)

    def test_admin_nao_desativa_a_propria_conta_por_delete(self):
        self.add_second_admin()

        response = self.client.delete(detail_url(self.admin))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('própria conta', str(response.data['detail']))
        self.assert_still_active_admin(self.admin)

    def test_admin_ainda_edita_os_proprios_dados_pessoais(self):
        response = self.client.patch(detail_url(self.admin), {'nome': 'Admin Renomeado'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nome, 'Admin Renomeado')
        self.assert_still_active_admin(self.admin)

    # Último administrador ativo ---------------------------------------------

    def test_ultimo_admin_ativo_nao_e_removido_nem_pela_plataforma(self):
        self.client.force_authenticate(self.superuser)

        attempts = [
            ('delete', None),
            ('patch', {'is_active': False}),
            ('patch', {'tipo_perfil': User.TipoPerfil.CLIENTE}),
        ]
        for method, payload in attempts:
            response = getattr(self.client, method)(detail_url(self.admin), payload, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, (method, payload))
            self.assertIn('sem nenhum administrador ativo', str(response.data))
            self.assert_still_active_admin(self.admin)

    def test_admin_inativo_nao_conta_como_administrador_restante(self):
        self.add_second_admin(is_active=False)
        self.client.force_authenticate(self.superuser)

        response = self.client.delete(detail_url(self.admin))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_still_active_admin(self.admin)

    def test_admin_de_outra_barbearia_nao_conta_como_administrador_restante(self):
        create_user('admin-b@example.com', User.TipoPerfil.ADMIN, create_barbershop('Barbearia Bairro'))
        self.client.force_authenticate(self.superuser)

        response = self.client.patch(detail_url(self.admin), {'tipo_perfil': User.TipoPerfil.CLIENTE}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_still_active_admin(self.admin)

    def test_remover_um_admin_e_permitido_quando_outro_permanece(self):
        second = self.add_second_admin()

        response = self.client.delete(detail_url(second))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        second.refresh_from_db()
        self.assertFalse(second.is_active)
        self.assert_still_active_admin(self.admin)

        # Agora o admin restante é o último e passa a ser protegido.
        self.client.force_authenticate(self.superuser)
        response = self.client.delete(detail_url(self.admin))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_still_active_admin(self.admin)

    def test_rebaixar_outro_admin_e_permitido_quando_um_permanece(self):
        second = self.add_second_admin()

        response = self.client.patch(detail_url(second), {'tipo_perfil': User.TipoPerfil.CLIENTE}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        second.refresh_from_db()
        self.assertEqual(second.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assert_still_active_admin(self.admin)

    # Gerenciamento legítimo dos demais usuários -----------------------------

    def test_admin_gerencia_clientes_e_barbeiros_normalmente(self):
        response = self.client.patch(detail_url(self.client_user), {'nome': 'Cliente Editado'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(detail_url(self.client_user), {'is_active': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.patch(detail_url(self.client_user), {'is_active': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        barber_user = self.barber.user
        response = self.client.patch(detail_url(barber_user), {'tipo_perfil': User.TipoPerfil.CLIENTE}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.barber.refresh_from_db()
        self.assertFalse(self.barber.ativo)

        response = self.client.delete(detail_url(self.client_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)

        self.assert_still_active_admin(self.admin)

    def test_cliente_continua_sem_acesso_a_gestao_de_usuarios(self):
        self.client.force_authenticate(self.client_user)

        self.assertEqual(self.client.delete(detail_url(self.admin)).status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(detail_url(self.client_user), {'tipo_perfil': User.TipoPerfil.ADMIN}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assert_still_active_admin(self.admin)


@skipUnless(connection.vendor == 'postgresql', 'Requer bloqueio real do PostgreSQL.')
class LastAdminConcurrencyTests(TransactionTestCase):
    """Dois admins removendo um ao outro ao mesmo tempo: só um pode vencer."""

    reset_sequences = True

    def setUp(self):
        self.shop = create_barbershop()
        self.admin_a = create_user('admin-a@example.com', User.TipoPerfil.ADMIN, self.shop)
        self.admin_b = create_user('admin-b@example.com', User.TipoPerfil.ADMIN, self.shop)

    def run_concurrently(self, *requests):
        """Executa as requisições em threads, liberadas juntas por uma barreira.

        A barreira fica antes da transação de cada operação: as duas leem o
        mesmo estado (dois admins ativos) e disputam a gravação.
        """
        barrier = threading.Barrier(len(requests))
        outcomes, failures = [], []
        original_destroy = UserViewSet.perform_destroy
        original_update = UserViewSet.perform_update

        def synchronized_destroy(view, instance):
            barrier.wait(timeout=10)
            return original_destroy(view, instance)

        def synchronized_update(view, serializer):
            barrier.wait(timeout=10)
            return original_update(view, serializer)

        def worker(actor, method, target, payload):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=actor.pk))
            try:
                response = getattr(client, method)(detail_url(target), payload, format='json')
                outcomes.append(response.status_code)
            except Exception as error:  # pragma: no cover - repropagado abaixo
                failures.append(error)
            finally:
                close_old_connections()

        with mock.patch.object(UserViewSet, 'perform_destroy', synchronized_destroy), \
                mock.patch.object(UserViewSet, 'perform_update', synchronized_update):
            threads = [threading.Thread(target=worker, args=request) for request in requests]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)

        self.assertFalse(failures, failures)
        return sorted(outcomes)

    def active_admins(self):
        return User.objects.filter(
            barbershop=self.shop, tipo_perfil=User.TipoPerfil.ADMIN, is_active=True,
        ).count()

    def test_desativacoes_cruzadas_simultaneas_mantem_um_admin(self):
        outcomes = self.run_concurrently(
            (self.admin_a, 'delete', self.admin_b, None),
            (self.admin_b, 'delete', self.admin_a, None),
        )

        self.assertEqual(outcomes, [status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST])
        self.assertEqual(self.active_admins(), 1)

    def test_rebaixamento_e_desativacao_simultaneos_mantem_um_admin(self):
        outcomes = self.run_concurrently(
            (self.admin_a, 'patch', self.admin_b, {'tipo_perfil': User.TipoPerfil.CLIENTE}),
            (self.admin_b, 'delete', self.admin_a, None),
        )

        # Vence a operação que obtiver a trava primeiro (PATCH → 200 ou
        # DELETE → 204); a outra precisa ser recusada.
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes.count(status.HTTP_400_BAD_REQUEST), 1)
        self.assertIn(outcomes[0], (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))
        self.assertEqual(self.active_admins(), 1)
