"""
BUS-01 (complemento) — a regra do último admin ativo vale em todos os caminhos.

Além da API (accounts/test_admin_protection.py), cobre o Django Admin
(formulário de edição, exclusão individual e exclusão em lote), o ORM
(save, delete, QuerySet.update/delete, bulk_update), o caminho de recuperação
(criar, ativar ou promover um substituto antes de remover o anterior) e a
concorrência no PostgreSQL.
"""
import threading
from datetime import time
from unittest import mock, skipUnless

from django.contrib.admin.models import DELETION, LogEntry
from django.db import close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts import admin_integrity
from accounts.admin import UserAdmin
from accounts.admin_integrity import (
    LAST_ADMIN_MESSAGE, SELF_DEACTIVATE_MESSAGE, SELF_DELETE_MESSAGE, SELF_ROLE_MESSAGE,
    AdminIntegrityError,
)
from accounts.models import User
from barbershops.models import Barbershop

PASSWORD = 'Senha-segura-123'
ADMIN, CLIENTE = User.TipoPerfil.ADMIN, User.TipoPerfil.CLIENTE


def create_shop(nome):
    return Barbershop.objects.create(
        nome=nome, endereco='Rua Principal, 100', telefone='11999999999',
        email=f'{nome.split()[-1].lower()}@example.com',
        horario_abertura=time(8), horario_fechamento=time(18),
    )


def create_user(email, perfil, shop, **extra):
    return User.objects.create_user(
        email=email, nome=email.split('@')[0].title(), password=PASSWORD,
        tipo_perfil=perfil, barbershop=shop, **extra,
    )


def active_admins(shop):
    return User.objects.filter(barbershop=shop, tipo_perfil=ADMIN, is_active=True).count()


def change_form_data(user, **overrides):
    """Dados do formulário de edição do Django Admin, como o navegador enviaria."""
    flags = {name: getattr(user, name) for name in ('is_active', 'is_staff', 'is_superuser')}
    for name in list(flags):
        if name in overrides:
            flags[name] = overrides.pop(name)
    data = {
        'email': user.email, 'nome': user.nome, 'tipo_perfil': user.tipo_perfil,
        'barbershop': user.barbershop_id or '',
    }
    data.update({name: 'on' for name, value in flags.items() if value})
    data.update(overrides)
    return data


class AdminSiteTestMixin:
    def setUp(self):
        self.shop = create_shop('Barbearia Central')
        self.other_shop = create_shop('Barbearia Bairro')
        self.admin = create_user('admin@example.com', ADMIN, self.shop)
        self.client_user = create_user('cliente@example.com', CLIENTE, self.shop)
        self.superuser = User.objects.create_superuser(
            email='plataforma@example.com', nome='Plataforma', password=PASSWORD,
        )
        self.client.force_login(self.superuser)

    def change(self, user, **overrides):
        return self.client.post(
            reverse('admin:accounts_user_change', args=[user.pk]), change_form_data(user, **overrides),
        )

    def bulk_delete(self, users, confirm=True):
        data = {'action': 'delete_selected', '_selected_action': [u.pk for u in users]}
        if confirm:
            data['post'] = 'yes'
        return self.client.post(reverse('admin:accounts_user_changelist'), data, follow=True)

    def messages_of(self, response):
        return [str(m) for m in response.context['messages']]

    def assert_active_admin(self, user, shop=None):
        user.refresh_from_db()
        self.assertEqual(
            (user.tipo_perfil, user.is_active, user.barbershop_id),
            (ADMIN, True, (shop or self.shop).pk),
        )


class DjangoAdminLastAdminTests(AdminSiteTestMixin, TestCase):
    # Rebaixamento, desativação e transferência do último admin ---------------

    def test_rebaixamento_do_ultimo_admin_e_recusado(self):
        response = self.change(self.admin, tipo_perfil=CLIENTE)

        self.assertContains(response, LAST_ADMIN_MESSAGE)
        self.assert_active_admin(self.admin)

    def test_desativacao_do_ultimo_admin_e_recusada(self):
        response = self.change(self.admin, is_active=False)

        self.assertContains(response, LAST_ADMIN_MESSAGE)
        self.assert_active_admin(self.admin)

    def test_transferencia_do_ultimo_admin_e_recusada(self):
        for destino in (self.other_shop.pk, ''):
            response = self.change(self.admin, barbershop=destino)

            self.assertContains(response, LAST_ADMIN_MESSAGE)
            self.assert_active_admin(self.admin)

    def test_edicao_comum_do_ultimo_admin_continua_permitida(self):
        response = self.change(self.admin, nome='Admin Renomeado')

        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nome, 'Admin Renomeado')

    # Exclusão individual ------------------------------------------------------

    def test_exclusao_do_ultimo_admin_e_recusada(self):
        url = reverse('admin:accounts_user_delete', args=[self.admin.pk])
        change_url = reverse('admin:accounts_user_change', args=[self.admin.pk])

        for response in (self.client.get(url), self.client.post(url, {'post': 'yes'})):
            self.assertRedirects(response, change_url, fetch_redirect_response=False)

        self.assert_active_admin(self.admin)
        response = self.client.get(change_url)
        self.assertIn(LAST_ADMIN_MESSAGE, self.messages_of(response))

    def test_usuario_sem_permissao_continua_recebendo_403(self):
        staff = User.objects.create_user(
            email='staff@example.com', nome='Staff', password=PASSWORD, is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get(reverse('admin:accounts_user_delete', args=[self.admin.pk]))

        self.assertEqual(response.status_code, 403)

    # Exclusão em lote --------------------------------------------------------

    def test_exclusao_em_lote_com_o_ultimo_admin_e_recusada(self):
        for confirm in (False, True):  # página de confirmação e confirmação final
            response = self.bulk_delete([self.admin, self.client_user], confirm=confirm)

            self.assertIn(LAST_ADMIN_MESSAGE, self.messages_of(response))

        self.assertTrue(User.objects.filter(pk__in=[self.admin.pk, self.client_user.pk]).count() == 2)
        self.assertFalse(LogEntry.objects.filter(action_flag=DELETION).exists())

    def test_exclusao_em_lote_de_todos_os_admins_e_recusada(self):
        second = create_user('admin2@example.com', ADMIN, self.shop)

        response = self.bulk_delete([self.admin, second])

        self.assertIn(LAST_ADMIN_MESSAGE, self.messages_of(response))
        self.assertEqual(active_admins(self.shop), 2)

    def test_exclusao_em_lote_que_preserva_um_admin_e_permitida(self):
        second = create_user('admin2@example.com', ADMIN, self.shop)

        response = self.bulk_delete([second, self.client_user])

        self.assertFalse(User.objects.filter(pk__in=[second.pk, self.client_user.pk]).exists())
        self.assertEqual(LogEntry.objects.filter(action_flag=DELETION).count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assert_active_admin(self.admin)

    # Autoalteração do superusuário -------------------------------------------

    def test_superusuario_nao_altera_o_proprio_perfil_nem_se_desativa(self):
        response = self.change(self.superuser, tipo_perfil=CLIENTE)
        self.assertContains(response, SELF_ROLE_MESSAGE)

        response = self.change(self.superuser, is_active=False)
        self.assertContains(response, SELF_DEACTIVATE_MESSAGE)

        self.superuser.refresh_from_db()
        self.assertEqual((self.superuser.tipo_perfil, self.superuser.is_active), (ADMIN, True))

    def test_superusuario_nao_exclui_a_propria_conta(self):
        url = reverse('admin:accounts_user_delete', args=[self.superuser.pk])
        self.client.post(url, {'post': 'yes'})

        response = self.bulk_delete([self.superuser])

        self.assertIn(SELF_DELETE_MESSAGE, self.messages_of(response))
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

    # Gerenciamento legítimo e recuperação -----------------------------------

    def test_rebaixar_outro_admin_com_substituto_e_permitido(self):
        create_user('admin2@example.com', ADMIN, self.shop)

        response = self.change(self.admin, tipo_perfil=CLIENTE)

        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.tipo_perfil, CLIENTE)
        self.assertEqual(active_admins(self.shop), 1)

    def test_recuperacao_criando_um_admin_substituto(self):
        response = self.client.post(reverse('admin:accounts_user_add'), {
            'email': 'substituto@example.com', 'nome': 'Substituto', 'tipo_perfil': ADMIN,
            'barbershop': self.shop.pk, 'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(active_admins(self.shop), 2)

        response = self.change(self.admin, tipo_perfil=CLIENTE)

        self.assertEqual(response.status_code, 302)
        self.assert_active_admin(User.objects.get(email='substituto@example.com'))

    def test_recuperacao_ativando_um_admin_inativo(self):
        substituto = create_user('admin2@example.com', ADMIN, self.shop, is_active=False)
        self.assertContains(self.change(self.admin, is_active=False), LAST_ADMIN_MESSAGE)

        self.assertEqual(self.change(substituto, is_active=True).status_code, 302)
        response = self.change(self.admin, is_active=False)

        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)
        self.assert_active_admin(substituto)

    def test_recuperacao_promovendo_um_cliente(self):
        self.assertEqual(self.change(self.client_user, tipo_perfil=ADMIN).status_code, 302)

        response = self.client.post(
            reverse('admin:accounts_user_delete', args=[self.admin.pk]), {'post': 'yes'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.admin.pk).exists())
        self.assert_active_admin(self.client_user)


class OrmPathsTests(TestCase):
    """Qualquer código que use o ORM (shell, scripts, futuras views)."""

    def setUp(self):
        self.shop = create_shop('Barbearia Central')
        self.admin = create_user('admin@example.com', ADMIN, self.shop)
        self.client_user = create_user('cliente@example.com', CLIENTE, self.shop)

    def assert_refused(self, operation):
        # Cada operação na própria transação, como numa requisição real:
        # bulk_update() usa atomic(savepoint=False) e, ao ser recusado, marca a
        # transação que o envolve para rollback.
        with self.assertRaises(AdminIntegrityError) as ctx, transaction.atomic():
            operation()
        self.assertIn(LAST_ADMIN_MESSAGE, ctx.exception.messages)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.tipo_perfil, self.admin.is_active, self.admin.barbershop_id),
                         (ADMIN, True, self.shop.pk))

    def test_save_recusa_rebaixar_desativar_ou_transferir(self):
        other = create_shop('Barbearia Bairro')
        for field, value in (('tipo_perfil', CLIENTE), ('is_active', False), ('barbershop', other), ('barbershop', None)):
            user = User.objects.get(pk=self.admin.pk)
            setattr(user, field, value)
            self.assert_refused(user.save)
            self.assert_refused(lambda: user.save(update_fields=[field]))

    def test_delete_recusa_o_ultimo_admin(self):
        self.assert_refused(User.objects.get(pk=self.admin.pk).delete)

    def test_operacoes_em_lote_recusam_o_ultimo_admin(self):
        admins = User.objects.filter(barbershop=self.shop, tipo_perfil=ADMIN)
        self.assert_refused(lambda: admins.update(is_active=False))
        self.assert_refused(lambda: admins.update(tipo_perfil=CLIENTE))
        self.assert_refused(lambda: User.objects.filter(barbershop=self.shop).delete())
        demoted = User.objects.get(pk=self.admin.pk)
        demoted.tipo_perfil = CLIENTE
        self.assert_refused(lambda: User.objects.bulk_update([demoted], ['tipo_perfil']))

    def test_lote_que_remove_todos_os_admins_e_recusado(self):
        create_user('admin2@example.com', ADMIN, self.shop)

        self.assert_refused(
            lambda: User.objects.filter(barbershop=self.shop, tipo_perfil=ADMIN).update(is_active=False)
        )
        self.assertEqual(active_admins(self.shop), 2)

    def test_operacoes_que_nao_afetam_o_ultimo_admin_continuam_livres(self):
        User.objects.filter(pk=self.admin.pk).update(nome='Renomeado')
        user = User.objects.get(pk=self.admin.pk)
        user.tipo_perfil = CLIENTE
        user.save(update_fields=['nome', 'last_login'])  # campos não protegidos
        User.objects.filter(pk=self.client_user.pk).update(is_active=False)
        User.objects.filter(pk=self.client_user.pk).delete()

        self.assertEqual(active_admins(self.shop), 1)

    def test_rebaixar_um_admin_quando_outro_permanece(self):
        second = create_user('admin2@example.com', ADMIN, self.shop)

        second.tipo_perfil = CLIENTE
        second.save()

        self.assertEqual(active_admins(self.shop), 1)

    def test_barbearia_sem_admin_ativo_nao_bloqueia_edicoes(self):
        legacy = create_shop('Barbearia Legada')
        inactive_admin = create_user('antigo@example.com', ADMIN, legacy, is_active=False)
        client = create_user('c@example.com', CLIENTE, legacy)

        inactive_admin.tipo_perfil = CLIENTE
        inactive_admin.save()
        client.delete()

    def test_superusuario_da_plataforma_sem_barbearia_nao_e_afetado(self):
        superuser = User.objects.create_superuser(email='p@example.com', nome='P', password=PASSWORD)

        superuser.is_active = False
        superuser.save()
        superuser.delete()

    def test_recusa_desfaz_apenas_a_propria_operacao(self):
        with transaction.atomic():
            User.objects.filter(pk=self.client_user.pk).update(nome='Mudou')
            with self.assertRaises(AdminIntegrityError):
                User.objects.filter(pk=self.admin.pk).update(is_active=False)

        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.nome, 'Mudou')
        self.assertEqual(active_admins(self.shop), 1)


class ApiRecoveryTests(APITestCase):
    def test_admin_reativa_substituto_pela_api_antes_de_o_anterior_ser_removido(self):
        shop = create_shop('Barbearia Central')
        admin = create_user('admin@example.com', ADMIN, shop)
        substituto = create_user('admin2@example.com', ADMIN, shop, is_active=False)
        superuser = User.objects.create_superuser(email='p@example.com', nome='P', password=PASSWORD)

        self.client.force_authenticate(superuser)
        self.assertEqual(self.client.delete(reverse('user-detail', args=[admin.pk])).status_code,
                         status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(admin)
        response = self.client.patch(reverse('user-detail', args=[substituto.pk]), {'is_active': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(superuser)
        self.assertEqual(self.client.delete(reverse('user-detail', args=[admin.pk])).status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertEqual(active_admins(shop), 1)


@skipUnless(connection.vendor == 'postgresql', 'Requer bloqueio real do PostgreSQL.')
class AdminPathsConcurrencyTests(TransactionTestCase):
    """Duas operações simultâneas sobre os dois admins: um sempre permanece."""

    reset_sequences = True

    def setUp(self):
        self.shop = create_shop('Barbearia Central')
        self.admin_a = create_user('admin-a@example.com', ADMIN, self.shop)
        self.admin_b = create_user('admin-b@example.com', ADMIN, self.shop)
        self.superuser = User.objects.create_superuser(
            email='plataforma@example.com', nome='Plataforma', password=PASSWORD,
        )

    def run_together(self, *jobs):
        results, failures = [], []

        def worker(job):
            close_old_connections()
            try:
                results.append(job())
            except Exception as error:  # noqa: BLE001 - classificado pelo teste
                failures.append(error)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=worker, args=(job,)) for job in jobs]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        return results, failures

    def synchronized(self, target, attribute, parties=2):
        """Segura as duas operações logo antes da etapa que disputa a trava."""
        barrier = threading.Barrier(parties)
        original = getattr(target, attribute)

        def wrapper(*args, **kwargs):
            barrier.wait(timeout=10)
            return original(*args, **kwargs)

        return mock.patch.object(target, attribute, wrapper)

    def admin_client(self):
        client = Client()
        client.force_login(User.objects.get(pk=self.superuser.pk))
        return client

    def test_django_admin_rebaixamento_e_desativacao_simultaneos(self):
        a_data = change_form_data(self.admin_a, tipo_perfil=CLIENTE)
        b_data = change_form_data(self.admin_b, is_active=False)

        def post(user, data):
            return lambda: self.admin_client().post(
                reverse('admin:accounts_user_change', args=[user.pk]), data,
            ).status_code

        with self.synchronized(UserAdmin, 'save_model'):
            results, failures = self.run_together(post(self.admin_a, a_data), post(self.admin_b, b_data))

        self.assertFalse(failures, failures)
        self.assertEqual(sorted(results), [302, 403])
        self.assertEqual(active_admins(self.shop), 1)

    def test_django_admin_exclusoes_em_lote_simultaneas(self):
        def bulk_delete(user):
            return lambda: self.admin_client().post(reverse('admin:accounts_user_changelist'), {
                'action': 'delete_selected', '_selected_action': [user.pk], 'post': 'yes',
            }).status_code

        with self.synchronized(UserAdmin, 'delete_queryset'):
            results, failures = self.run_together(bulk_delete(self.admin_a), bulk_delete(self.admin_b))

        self.assertFalse(failures, failures)
        self.assertEqual(results, [302, 302])
        self.assertEqual(active_admins(self.shop), 1)
        # O histórico da exclusão recusada também foi desfeito.
        self.assertEqual(LogEntry.objects.filter(action_flag=DELETION).count(), 1)

    def test_orm_update_e_delete_simultaneos(self):
        jobs = (
            lambda: User.objects.filter(pk=self.admin_a.pk).update(is_active=False),
            lambda: User.objects.get(pk=self.admin_b.pk).delete(),
        )

        with self.synchronized(admin_integrity, 'lock_active_admins'):
            results, failures = self.run_together(*jobs)

        self.assertEqual(len(results), 1)
        self.assertEqual([type(f) for f in failures], [AdminIntegrityError])
        self.assertEqual(active_admins(self.shop), 1)
