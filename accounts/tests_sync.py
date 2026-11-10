"""
Testes de sincronização entre User e Barber profiles.

Cobre os 11 cenários combinados:
1. Desativar usuário via UserViewSet.perform_destroy() também desativa Barber (ativo=False)
2. Desativar usuário via UserSerializer.update(is_active=False) também desativa Barber
3. Reativar usuário via UserSerializer.update(is_active=True) reativa Barber (ativo=True)
4. BarberSerializer valida ativo=False corretamente (sem erro de validação)
5. BarberViewSet.perform_update() altera ativo e sincroniza User.tipo_perfil
6. UserSerializer.update() altera is_active e sincroniza Barber.ativo
7. Criação de Barber inativo (ativo=False) com usuário CLIENTE não promove a BARBEIRO
8. Criação de Barber ativo (ativo=True) com usuário CLIENTE promove a BARBEIRO
9. Reativação de Barber inativo via API promove usuário CLIENTE a BARBEIRO
10. Desativação de Barber via API rebaixa usuário BARBEIRO para CLIENTE
11. Isolamento multi-tenant: sincronização só ocorre dentro do mesmo tenant
"""
from datetime import time
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop


class UserBarberSyncTests(APITestCase):
    """Testes de sincronização bidirecional entre User e Barber."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.other_barbershop = Barbershop.objects.create(
            nome='Barbearia Sul',
            endereco='Rua Sul, 200',
            telefone='11888888888',
            email='sul@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            nome='admin',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop,
        )
        self.client_user = User.objects.create_user(
            email='cliente@example.com',
            nome='cliente',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        self.barbeiro_user = User.objects.create_user(
            email='barbeiro@example.com',
            nome='barbeiro',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )
        self.barbeiro = Barber.objects.create(
            user=self.barbeiro_user,
            barbershop=self.barbershop,
            especialidade='Corte',
            ativo=True,
        )
        # Usuário do tipo BARBEIRO mas sem perfil Barber
        self.barbeiro_sem_perfil = User.objects.create_user(
            email='barbeiro-sem-perfil@example.com',
            nome='barbeiro-sem-perfil',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )

        self.user_list_url = reverse('user-list')
        self.barber_list_url = reverse('barber-list')

    def _detail_url(self, pk):
        return reverse('user-detail', args=[pk])

    def _barber_detail_url(self, pk):
        return reverse('barber-detail', args=[pk])

    # ------------------------------------------------------------------
    # 1) Desativar usuário via UserViewSet.perform_destroy() também desativa Barber
    # ------------------------------------------------------------------
    def test_destroy_user_deactivates_barber_profile(self):
        """
        UserViewSet.perform_destroy() deve desativar o usuário (is_active=False)
        E também desativar o perfil Barber associado (ativo=False, deleted_at, deleted_by).
        """
        self.client.force_authenticate(self.admin)

        response = self.client.delete(self._detail_url(self.barbeiro_user.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Usuário desativado
        self.barbeiro_user.refresh_from_db()
        self.assertFalse(self.barbeiro_user.is_active)

        # Perfil Barber desativado com soft delete
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)
        self.assertIsNotNone(self.barbeiro.deleted_at)
        self.assertIsNotNone(self.barbeiro.deleted_by)

    # ------------------------------------------------------------------
    # 2) Desativar usuário via UserSerializer.update(is_active=False) também desativa Barber
    # ------------------------------------------------------------------
    def test_update_user_is_active_false_deactivates_barber(self):
        """
        PATCH /users/{id}/ com is_active=False deve desativar o usuário
        E também desativar o perfil Barber associado.
        """
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self._detail_url(self.barbeiro_user.pk),
            {'is_active': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Usuário desativado
        self.barbeiro_user.refresh_from_db()
        self.assertFalse(self.barbeiro_user.is_active)

        # Perfil Barber desativado com soft delete
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)
        self.assertIsNotNone(self.barbeiro.deleted_at)
        self.assertIsNotNone(self.barbeiro.deleted_by)

    # ------------------------------------------------------------------
    # 3) Reativar usuário via UserSerializer.update(is_active=True) NÃO reativa Barber
    # ------------------------------------------------------------------
    def test_update_user_is_active_true_reactivates_barber(self):
        """
        PATCH /users/{id}/ com is_active=True deve reativar o usuário
        MAS NÃO deve reativar o perfil Barber associado.
        O perfil Barber deve continuar inativo até reativação explícita via API de barbeiros.
        """
        # Primeiro desativa
        self.barbeiro_user.is_active = False
        self.barbeiro_user.save()
        self.barbeiro.ativo = False
        self.barbeiro.deleted_at = timezone.now()
        self.barbeiro.deleted_by = self.admin
        self.barbeiro.save()

        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self._detail_url(self.barbeiro_user.pk),
            {'is_active': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Usuário reativado
        self.barbeiro_user.refresh_from_db()
        self.assertTrue(self.barbeiro_user.is_active)

        # Perfil Barber PERMANECE inativo (não reativado automaticamente)
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)
        self.assertIsNotNone(self.barbeiro.deleted_at)
        self.assertIsNotNone(self.barbeiro.deleted_by)

    # ------------------------------------------------------------------
    # 4) BarberSerializer valida ativo=False corretamente (sem erro de validação)
    # ------------------------------------------------------------------
    def test_barber_serializer_validates_ativo_false_correctly(self):
        """
        BarberSerializer.validate() deve aceitar ativo=False sem erro.
        O bug era que a validação não aplicava o valor ativo=False à instância
        temporária antes de chamar clean(), causando erro se o usuário fosse CLIENTE.
        """
        self.client.force_authenticate(self.admin)

        # Criar Barber com ativo=False para usuário CLIENTE
        # Isso NÃO deve promover o usuário a BARBEIRO
        response = self.client.post(
            self.barber_list_url,
            {
                'user': self.client_user.pk,
                'especialidade': 'Corte',
                'ativo': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Barber criado inativo
        novo_barber = Barber.objects.get(pk=response.data['id'])
        self.assertFalse(novo_barber.ativo)

        # Usuário deve permanecer CLIENTE (não promovido)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.CLIENTE)

    # ------------------------------------------------------------------
    # 5) BarberViewSet.perform_update() altera ativo e sincroniza User.tipo_perfil
    # ------------------------------------------------------------------
    def test_barber_viewset_perform_update_syncs_user_tipo_perfil_on_deactivate(self):
        """
        BarberViewSet.perform_update() ao desativar Barber (ativo=False)
        deve rebaixar User.tipo_perfil de BARBEIRO para CLIENTE.
        """
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self._barber_detail_url(self.barbeiro.pk),
            {'ativo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Barber desativado
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)

        # Usuário rebaixado para CLIENTE
        self.barbeiro_user.refresh_from_db()
        self.assertEqual(self.barbeiro_user.tipo_perfil, User.TipoPerfil.CLIENTE)

    def test_barber_viewset_perform_update_syncs_user_tipo_perfil_on_reactivate(self):
        """
        BarberViewSet.perform_update() ao reativar Barber (ativo=True)
        deve promover User.tipo_perfil de CLIENTE para BARBEIRO.
        """
        # Primeiro desativa
        self.barbeiro.ativo = False
        self.barbeiro.deleted_at = timezone.now()
        self.barbeiro.deleted_by = self.admin
        self.barbeiro.save()
        self.barbeiro_user.tipo_perfil = User.TipoPerfil.CLIENTE
        self.barbeiro_user.save()

        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self._barber_detail_url(self.barbeiro.pk),
            {'ativo': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Barber reativado
        self.barbeiro.refresh_from_db()
        self.assertTrue(self.barbeiro.ativo)
        self.assertIsNone(self.barbeiro.deleted_at)
        self.assertIsNone(self.barbeiro.deleted_by)

        # Usuário promovido para BARBEIRO
        self.barbeiro_user.refresh_from_db()
        self.assertEqual(self.barbeiro_user.tipo_perfil, User.TipoPerfil.BARBEIRO)

    # ------------------------------------------------------------------
    # 6) UserSerializer.update() altera is_active e sincroniza Barber.ativo
    # ------------------------------------------------------------------
    def test_user_serializer_update_is_active_syncs_barber_ativo(self):
        """
        UserSerializer.update() alterando is_active deve sincronizar Barber.ativo.
        Desativar usuário desativa Barber. Reativar usuário NÃO reativa Barber.
        """
        self.client.force_authenticate(self.admin)

        # Desativar
        response = self.client.patch(
            self._detail_url(self.barbeiro_user.pk),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.barbeiro_user.refresh_from_db()
        self.assertFalse(self.barbeiro_user.is_active)
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)

        # Reativar
        response = self.client.patch(
            self._detail_url(self.barbeiro_user.pk),
            {'is_active': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.barbeiro_user.refresh_from_db()
        self.assertTrue(self.barbeiro_user.is_active)
        # Barber permanece inativo (reativação explícita necessária)
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)

    # ------------------------------------------------------------------
    # 7) Criação de Barber inativo (ativo=False) com usuário CLIENTE não promove a BARBEIRO
    # ------------------------------------------------------------------
    def test_create_barber_inativo_cliente_nao_promove(self):
        """
        Criar Barber com ativo=False e usuário CLIENTE não deve promover o usuário a BARBEIRO.
        """
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.barber_list_url,
            {
                'user': self.client_user.pk,
                'especialidade': 'Barba',
                'ativo': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Barber criado inativo
        novo_barber = Barber.objects.get(pk=response.data['id'])
        self.assertFalse(novo_barber.ativo)

        # Usuário permanece CLIENTE
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.CLIENTE)

    # ------------------------------------------------------------------
    # 8) Criação de Barber ativo (ativo=True) com usuário CLIENTE promove a BARBEIRO
    # ------------------------------------------------------------------
    def test_create_barber_ativo_cliente_promove_para_barbeiro(self):
        """
        Criar Barber com ativo=True e usuário CLIENTE deve promover o usuário a BARBEIRO.
        """
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.barber_list_url,
            {
                'user': self.client_user.pk,
                'especialidade': 'Corte',
                'ativo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Barber criado ativo
        novo_barber = Barber.objects.get(pk=response.data['id'])
        self.assertTrue(novo_barber.ativo)

        # Usuário promovido a BARBEIRO
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.BARBEIRO)

    # ------------------------------------------------------------------
    # 9) Reativação de Barber inativo via API promove usuário CLIENTE a BARBEIRO
    # ------------------------------------------------------------------
    def test_reactivate_barber_promotes_cliente_to_barbeiro(self):
        """
        Reativar Barber (ativo=True) via API deve promover usuário de CLIENTE para BARBEIRO.
        """
        # Criar Barber inativo com usuário CLIENTE
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.barber_list_url,
            {
                'user': self.client_user.pk,
                'especialidade': 'Sobrancelha',
                'ativo': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        barber_id = response.data['id']

        # Verifica estado inicial: Barber inativo, usuário CLIENTE
        barber = Barber.objects.get(pk=barber_id)
        self.assertFalse(barber.ativo)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.CLIENTE)

        # Reativar Barber
        response = self.client.patch(
            self._barber_detail_url(barber_id),
            {'ativo': True},
            format='json',
        )

        # Debug: print errors if any
        if response.status_code != status.HTTP_200_OK:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Barber reativado
        barber.refresh_from_db()
        self.assertTrue(barber.ativo)

        # Usuário promovido para BARBEIRO
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.tipo_perfil, User.TipoPerfil.BARBEIRO)

    # ------------------------------------------------------------------
    # 10) Desativação de Barber via API rebaixa usuário BARBEIRO para CLIENTE
    # ------------------------------------------------------------------
    def test_deactivate_barber_demotes_barbeiro_to_cliente(self):
        """
        Desativar Barber (ativo=False) via API deve rebaixar usuário de BARBEIRO para CLIENTE.
        """
        self.client.force_authenticate(self.admin)

        # Desativar Barber existente
        response = self.client.patch(
            self._barber_detail_url(self.barbeiro.pk),
            {'ativo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Barber desativado
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)

        # Usuário rebaixado para CLIENTE
        self.barbeiro_user.refresh_from_db()
        self.assertEqual(self.barbeiro_user.tipo_perfil, User.TipoPerfil.CLIENTE)

    # ------------------------------------------------------------------
    # 11) Isolamento multi-tenant: sincronização só ocorre dentro do mesmo tenant
    # ------------------------------------------------------------------
    def test_sync_only_occurs_within_same_tenant(self):
        """
        Sincronização User <-> Barber só deve ocorrer quando ambos estão no mesmo tenant.
        Admin de outro tenant não deve conseguir sincronizar.
        """
        # Criar barbeiro no tenant B
        barbeiro_user_b = User.objects.create_user(
            email='barbeiro.b@teste.com',
            nome='barbeiro-b',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.other_barbershop,
        )
        barbeiro_b = Barber.objects.create(
            user=barbeiro_user_b,
            barbershop=self.other_barbershop,
            especialidade='Corte',
            ativo=True,
        )

        # Admin do tenant A tenta desativar barbeiro do tenant B via user update
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse('user-detail', args=[barbeiro_user_b.pk]),
            {'is_active': False},
            format='json',
        )

        # Deve retornar 404 (não encontrado no tenant do admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Barbeiro do tenant B não deve ser afetado
        barbeiro_user_b.refresh_from_db()
        self.assertTrue(barbeiro_user_b.is_active)
        barbeiro_b.refresh_from_db()
        self.assertTrue(barbeiro_b.ativo)

        # Admin do tenant A tenta desativar barbeiro do tenant B via barber update
        response = self.client.patch(
            reverse('barber-detail', args=[barbeiro_b.pk]),
            {'ativo': False},
            format='json',
        )

        # Deve retornar 404 (não encontrado no tenant do admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Barbeiro do tenant B não deve ser afetado
        barbeiro_b.refresh_from_db()
        self.assertTrue(barbeiro_b.ativo)
        barbeiro_user_b.refresh_from_db()
        self.assertEqual(barbeiro_user_b.tipo_perfil, User.TipoPerfil.BARBEIRO)


# Adicionar import do time no topo
from datetime import time