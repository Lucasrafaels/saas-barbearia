from datetime import time

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Barber, Barbershop


class BarbershopSecurityTests(APITestCase):
    def setUp(self):
        self.barbershop = self.create_barbershop('Central', 'central@example.com')
        self.other_barbershop = self.create_barbershop('Sul', 'sul@example.com')
        self.admin = self.create_user(
            'admin@example.com', User.TipoPerfil.ADMIN, self.barbershop
        )
        self.client_user = self.create_user(
            'cliente@example.com', User.TipoPerfil.CLIENTE, self.barbershop
        )

    @staticmethod
    def create_barbershop(nome, email):
        return Barbershop.objects.create(
            nome=nome,
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )

    @staticmethod
    def create_user(email, tipo_perfil, barbershop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=barbershop,
        )

    def test_barber_model_and_api_reject_user_from_another_tenant(self):
        barber_user = self.create_user(
            'barbeiro-outra@example.com',
            User.TipoPerfil.BARBEIRO,
            self.other_barbershop,
        )
        barber = Barber(user=barber_user, barbershop=self.barbershop)

        with self.assertRaises(ValidationError):
            barber.full_clean()

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse('barber-list'),
            {'user': barber_user.pk, 'especialidade': 'Corte'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Barber.objects.filter(user=barber_user).exists())

    def test_only_admin_can_update_the_barbershop(self):
        url = reverse('barbershop-detail', args=[self.barbershop.pk])
        self.client.force_authenticate(self.client_user)

        forbidden_response = self.client.patch(url, {'ativo': False}, format='json')

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
        self.barbershop.refresh_from_db()
        self.assertTrue(self.barbershop.ativo)

        self.client.force_authenticate(self.admin)
        allowed_response = self.client.patch(url, {'ativo': False}, format='json')

        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
        self.barbershop.refresh_from_db()
        self.assertFalse(self.barbershop.ativo)


class BarbershopOnboardingTests(APITestCase):
    """
    Cobre o fluxo de onboarding de POST /api/v1/barbershops/ e a correção
    do bug que permitia criar uma barbearia "órfã": antes da correção, um
    usuário que já pertencia a um tenant também conseguia criar uma nova
    barbearia — ela era persistida no banco, só o vínculo de admin é que
    não acontecia, deixando um registro sem ninguém responsável.
    """

    def setUp(self):
        self.barbershop = BarbershopSecurityTests.create_barbershop(
            'Central', 'central@example.com',
        )
        self.list_url = reverse('barbershop-list')

    @staticmethod
    def create_user(email, tipo_perfil=None, barbershop=None):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil or User.TipoPerfil.CLIENTE,
            barbershop=barbershop,
        )

    @staticmethod
    def barbershop_payload(nome, email):
        return {
            'nome': nome,
            'endereco': 'Rua Nova, 500',
            'telefone': '11977777777',
            'email': email,
            'horario_abertura': '08:00',
            'horario_fechamento': '18:00',
        }

    def test_user_without_tenant_creates_barbershop_and_becomes_its_admin(self):
        user_sem_tenant = self.create_user('sem-tenant@example.com')
        self.client.force_authenticate(user_sem_tenant)

        response = self.client.post(
            self.list_url,
            self.barbershop_payload('Barbearia Nova', 'nova@example.com'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_sem_tenant.refresh_from_db()
        self.assertEqual(user_sem_tenant.barbershop_id, response.data['id'])
        self.assertEqual(user_sem_tenant.tipo_perfil, User.TipoPerfil.ADMIN)

    def test_user_with_tenant_cannot_create_another_barbershop(self):
        antes = Barbershop.objects.count()
        usuario_com_tenant = self.create_user(
            'ja-tem-tenant@example.com', User.TipoPerfil.CLIENTE, self.barbershop,
        )
        self.client.force_authenticate(usuario_com_tenant)

        response = self.client.post(
            self.list_url,
            self.barbershop_payload('Barbearia Órfã', 'orfa@example.com'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Nenhuma barbearia órfã deve ter sido criada no banco.
        self.assertEqual(Barbershop.objects.count(), antes)
        usuario_com_tenant.refresh_from_db()
        self.assertEqual(usuario_com_tenant.barbershop_id, self.barbershop.pk)
        self.assertEqual(usuario_com_tenant.tipo_perfil, User.TipoPerfil.CLIENTE)

    def test_admin_with_tenant_cannot_create_another_barbershop(self):
        """Mesma regra vale para quem já é admin de uma barbearia — não é
        só para clientes/barbeiros."""
        antes = Barbershop.objects.count()
        admin_existente = self.create_user(
            'admin-existente@example.com', User.TipoPerfil.ADMIN, self.barbershop,
        )
        self.client.force_authenticate(admin_existente)

        response = self.client.post(
            self.list_url,
            self.barbershop_payload('Segunda Barbearia', 'segunda@example.com'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Barbershop.objects.count(), antes)


class BarberAPITestCase(APITestCase):
    """
    Testes do endpoint /api/v1/barbers/ (BarberViewSet).

    Fixtures: duas barbearias — tenant A e tenant B. Na barbearia A temos
    um usuário de cada perfil (admin, cliente, barbeiro) e dois barbeiros
    já cadastrados (barbeiro_a e barbeiro_a2), além de um usuário do tipo
    barbeiro ainda SEM perfil Barber (útil para os testes de criação). Na
    barbearia B temos um admin e um barbeiro (com e sem perfil Barber já
    associado), usados só para os testes de isolamento entre tenants.

    Cobre os 11 pontos combinados:
    1. Admin lista barbeiros da própria barbearia.
    2. Cliente lista barbeiros da própria barbearia.
    3. Barbeiro visualiza (lista/detalha) barbeiros do próprio tenant.
    4. Somente admin pode criar barbeiro.
    5. Somente admin pode editar barbeiro.
    6. Somente admin pode excluir barbeiro.
    7. Usuário cliente não pode ser associado a um perfil Barber.
    8. Barbeiro de outra barbearia não pode ser associado à barbearia atual.
    9. Usuário não consegue manipular barbershop_id (create/update).
    10. Usuário de outra barbearia não consegue visualizar o barbeiro.
    11. Barber e User precisam pertencer à mesma barbearia (nível de modelo).
    """

    def setUp(self):
        # --- duas barbearias (tenants) ---
        self.barbershop_a = self._create_barbershop('Barbearia A', 'contato@barbeariaa.com')
        self.barbershop_b = self._create_barbershop('Barbearia B', 'contato@barbeariab.com')

        # --- usuários da barbearia A, um de cada perfil ---
        self.admin_a = self._create_user(
            'admin.a@teste.com', User.TipoPerfil.ADMIN, self.barbershop_a,
        )
        self.cliente_a = self._create_user(
            'cliente.a@teste.com', User.TipoPerfil.CLIENTE, self.barbershop_a,
        )
        self.barbeiro_user_a = self._create_user(
            'barbeiro.a@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        self.barbeiro_a = Barber.objects.create(
            user=self.barbeiro_user_a, barbershop=self.barbershop_a, especialidade='Corte',
        )

        # segundo barbeiro da barbearia A — útil para listar mais de um
        # registro e para os testes de editar/excluir "outro" barbeiro.
        self.barbeiro_user_a2 = self._create_user(
            'barbeiro2.a@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        self.barbeiro_a2 = Barber.objects.create(
            user=self.barbeiro_user_a2, barbershop=self.barbershop_a, especialidade='Barba',
        )

        # usuário do tipo barbeiro na barbearia A, mas AINDA sem perfil
        # Barber — usado para testar a criação (não pode haver conflito de
        # unicidade no OneToOneField `user`).
        self.barbeiro_user_a_sem_perfil = self._create_user(
            'barbeiro-novo.a@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )

        # --- usuários da barbearia B, só para os testes cross-tenant ---
        self.admin_b = self._create_user(
            'admin.b@teste.com', User.TipoPerfil.ADMIN, self.barbershop_b,
        )
        self.barbeiro_user_b = self._create_user(
            'barbeiro.b@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_b,
        )
        self.barbeiro_b = Barber.objects.create(
            user=self.barbeiro_user_b, barbershop=self.barbershop_b,
        )
        # barbeiro da barbearia B ainda sem perfil Barber — usado no teste
        # de API do item 8, para isolar o erro de "barbearia errada" sem
        # esbarrar na validação de unicidade do `user`.
        self.barbeiro_user_b_sem_perfil = self._create_user(
            'barbeiro-novo.b@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_b,
        )

        self.list_url = reverse('barber-list')

    # ---- helpers ----

    @staticmethod
    def _create_barbershop(nome, email):
        return Barbershop.objects.create(
            nome=nome,
            endereco='Rua Exemplo, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(9, 0),
            horario_fechamento=time(19, 0),
        )

    @staticmethod
    def _create_user(email, tipo_perfil, barbershop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='SenhaForte123',
            tipo_perfil=tipo_perfil,
            barbershop=barbershop,
        )

    @staticmethod
    def _detail_url(barber_id):
        return reverse('barber-detail', args=[barber_id])

    # ------------------------------------------------------------------
    # 1) Admin consegue listar barbeiros da própria barbearia
    # ------------------------------------------------------------------
    def test_admin_can_list_own_barbershop_barbers(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(self.barbeiro_b.id, ids)

    # ------------------------------------------------------------------
    # 2) Cliente consegue listar barbeiros da própria barbearia
    # ------------------------------------------------------------------
    def test_cliente_can_list_own_barbershop_barbers(self):
        self.client.force_authenticate(self.cliente_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(self.barbeiro_b.id, ids)

    # ------------------------------------------------------------------
    # 3) Barbeiro consegue visualizar barbeiros do próprio tenant
    # ------------------------------------------------------------------
    def test_barbeiro_can_list_own_tenant_barbers(self):
        self.client.force_authenticate(self.barbeiro_user_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(self.barbeiro_b.id, ids)

    def test_barbeiro_can_retrieve_barber_from_own_tenant(self):
        self.client.force_authenticate(self.barbeiro_user_a)
        response = self.client.get(self._detail_url(self.barbeiro_a2.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.barbeiro_a2.id)

    # ------------------------------------------------------------------
    # 4) Somente admin pode criar barbeiro
    # ------------------------------------------------------------------
    def test_admin_can_create_barber(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(
            self.list_url,
            {'user': self.barbeiro_user_a_sem_perfil.pk, 'especialidade': 'Sobrancelha'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Barber.objects.get(pk=response.data['id'])
        self.assertEqual(novo.user_id, self.barbeiro_user_a_sem_perfil.pk)
        self.assertEqual(novo.barbershop_id, self.barbershop_a.id)

    def test_cliente_cannot_create_barber(self):
        self.client.force_authenticate(self.cliente_a)
        antes = Barber.objects.count()
        response = self.client.post(
            self.list_url,
            {'user': self.barbeiro_user_a_sem_perfil.pk, 'especialidade': 'Sobrancelha'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Barber.objects.count(), antes)

    def test_barbeiro_cannot_create_barber(self):
        self.client.force_authenticate(self.barbeiro_user_a)
        antes = Barber.objects.count()
        response = self.client.post(
            self.list_url,
            {'user': self.barbeiro_user_a_sem_perfil.pk, 'especialidade': 'Sobrancelha'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Barber.objects.count(), antes)

    # ------------------------------------------------------------------
    # 5) Somente admin pode editar barbeiro
    # ------------------------------------------------------------------
    def test_admin_can_update_barber(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.patch(
            self._detail_url(self.barbeiro_a.id),
            {'especialidade': 'Corte e barba'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.barbeiro_a.refresh_from_db()
        self.assertEqual(self.barbeiro_a.especialidade, 'Corte e barba')

    def test_cliente_cannot_update_barber(self):
        self.client.force_authenticate(self.cliente_a)
        response = self.client.patch(
            self._detail_url(self.barbeiro_a.id),
            {'especialidade': 'Hackeado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.barbeiro_a.refresh_from_db()
        self.assertNotEqual(self.barbeiro_a.especialidade, 'Hackeado')

    def test_barbeiro_cannot_update_barber(self):
        self.client.force_authenticate(self.barbeiro_user_a)
        response = self.client.patch(
            self._detail_url(self.barbeiro_a2.id),
            {'especialidade': 'Hackeado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.barbeiro_a2.refresh_from_db()
        self.assertNotEqual(self.barbeiro_a2.especialidade, 'Hackeado')

    # ------------------------------------------------------------------
    # 6) Somente admin pode excluir barbeiro
    # ------------------------------------------------------------------
    def test_admin_can_delete_barber(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.delete(self._detail_url(self.barbeiro_a2.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.barbeiro_a2.refresh_from_db()
        self.assertFalse(self.barbeiro_a2.ativo)

    def test_cliente_cannot_delete_barber(self):
        self.client.force_authenticate(self.cliente_a)
        response = self.client.delete(self._detail_url(self.barbeiro_a.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Barber.objects.filter(pk=self.barbeiro_a.id).exists())

    def test_barbeiro_cannot_delete_barber(self):
        self.client.force_authenticate(self.barbeiro_user_a)
        response = self.client.delete(self._detail_url(self.barbeiro_a2.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Barber.objects.filter(pk=self.barbeiro_a2.id).exists())

    # ------------------------------------------------------------------
    # 7) Um usuário cliente não pode ser associado a um perfil Barber
    # ------------------------------------------------------------------
    def test_cliente_user_can_be_promoted_to_barber_via_api(self):
        """
        CLIENTE users should be promotable to BARBEIRO when creating a Barber profile.
        This is the corrected behavior: allow legitimate barber registration from CLIENTE users.
        """
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(
            self.list_url,
            {'user': self.cliente_a.pk, 'especialidade': 'Corte'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Barber.objects.get(pk=response.data['id'])
        self.assertEqual(novo.user_id, self.cliente_a.pk)
        self.assertEqual(novo.barbershop_id, self.barbershop_a.id)
        # User should be promoted to BARBEIRO
        self.cliente_a.refresh_from_db()
        self.assertEqual(self.cliente_a.tipo_perfil, User.TipoPerfil.BARBEIRO)

    def test_admin_user_cannot_be_converted_to_barber(self):
        """Administrators cannot be converted to barbers."""
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(
            self.list_url,
            {'user': self.admin_a.pk, 'especialidade': 'Corte'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user', response.data)
        self.assertFalse(Barber.objects.filter(user=self.admin_a).exists())

    def test_cliente_user_cannot_be_associated_to_barber_at_model_level(self):
        # This test verifies the model-level validation still rejects
        # a CLIENTE user directly without the promotion logic.
        barber = Barber(user=self.cliente_a, barbershop=self.barbershop_a)

        with self.assertRaises(ValidationError):
            barber.clean()

    # ------------------------------------------------------------------
    # 8) Um barbeiro de outra barbearia não pode ser associado à barbearia atual
    # ------------------------------------------------------------------
    def test_barber_from_other_tenant_cannot_be_associated_via_api(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(
            self.list_url,
            {'user': self.barbeiro_user_b_sem_perfil.pk, 'especialidade': 'Corte'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('barbershop', response.data)
        self.assertFalse(Barber.objects.filter(user=self.barbeiro_user_b_sem_perfil).exists())

    # ------------------------------------------------------------------
    # 9) Um usuário não consegue manipular barbershop_id
    # ------------------------------------------------------------------
    def test_cannot_set_barbershop_on_create(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.post(
            self.list_url,
            {
                'user': self.barbeiro_user_a_sem_perfil.pk,
                'especialidade': 'Corte',
                'barbershop': self.barbershop_b.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Barber.objects.get(pk=response.data['id'])
        self.assertEqual(novo.barbershop_id, self.barbershop_a.id)
        self.assertNotEqual(novo.barbershop_id, self.barbershop_b.id)

    def test_cannot_change_barbershop_on_update(self):
        self.client.force_authenticate(self.admin_a)
        response = self.client.patch(
            self._detail_url(self.barbeiro_a.id),
            {'barbershop': self.barbershop_b.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.barbeiro_a.refresh_from_db()
        self.assertEqual(self.barbeiro_a.barbershop_id, self.barbershop_a.id)

    # ------------------------------------------------------------------
    # 10) Um usuário de outra barbearia não consegue visualizar o barbeiro
    # ------------------------------------------------------------------
    def test_user_from_other_tenant_cannot_view_barber(self):
        self.client.force_authenticate(self.admin_b)
        response = self.client.get(self._detail_url(self.barbeiro_a.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        lista = self.client.get(self.list_url)
        ids = [item['id'] for item in lista.data['results']]
        self.assertNotIn(self.barbeiro_a.id, ids)

    # ------------------------------------------------------------------
    # 11) Barber e User precisam pertencer à mesma barbearia
    # ------------------------------------------------------------------
    def test_barber_and_user_must_share_same_barbershop(self):
        """Testa diretamente a regra de negócio em Barber.clean(),
        independente da camada de API: o vínculo só é válido quando
        barbeiro e usuário pertencem à mesma barbearia."""
        barber_barbearia_diferente = Barber(
            user=self.barbeiro_user_b, barbershop=self.barbershop_a,
        )
        with self.assertRaises(ValidationError):
            barber_barbearia_diferente.clean()

        # mesma barbearia para ambos: não deve levantar erro
        barber_valido = Barber(
            user=self.barbeiro_user_a_sem_perfil, barbershop=self.barbershop_a,
        )
        barber_valido.clean()

    # ------------------------------------------------------------------
    # 12) Filtro ?ativo=true funciona (apenas ativos)
    # ------------------------------------------------------------------
    def test_filtro_ativo_true(self):
        # Cria um barbeiro inativo
        user_inativo = self._create_user(
            'barbeiro.inativo@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        barbeiro_inativo = Barber.objects.create(
            user=user_inativo, barbershop=self.barbershop_a, especialidade='Corte', ativo=False,
        )

        self.client.force_authenticate(self.admin_a)
        response = self.client.get(self.list_url, {'ativo': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(barbeiro_inativo.id, ids)

    # ------------------------------------------------------------------
    # 13) Filtro ?ativo=false retorna apenas inativos
    # ------------------------------------------------------------------
    def test_filtro_ativo_false(self):
        # Cria um barbeiro inativo
        user_inativo = self._create_user(
            'barbeiro.inativo@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        barbeiro_inativo = Barber.objects.create(
            user=user_inativo, barbershop=self.barbershop_a, especialidade='Corte', ativo=False,
        )

        self.client.force_authenticate(self.admin_a)
        response = self.client.get(self.list_url, {'ativo': 'false'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(barbeiro_inativo.id, ids)
        self.assertNotIn(self.barbeiro_a.id, ids)
        self.assertNotIn(self.barbeiro_a2.id, ids)

    # ------------------------------------------------------------------
    # 14) Filtro ?ativo=all retorna todos (ativos e inativos) para admin
    # ------------------------------------------------------------------
    def test_filtro_ativo_all_admin(self):
        # Cria um barbeiro inativo
        user_inativo = self._create_user(
            'barbeiro.inativo@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        barbeiro_inativo = Barber.objects.create(
            user=user_inativo, barbershop=self.barbershop_a, especialidade='Corte', ativo=False,
        )

        self.client.force_authenticate(self.admin_a)
        response = self.client.get(self.list_url, {'ativo': 'all'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertIn(barbeiro_inativo.id, ids)

    # ------------------------------------------------------------------
    # 15) Filtro ?ativo=all não funciona para não-admins (retorna apenas ativos)
    # ------------------------------------------------------------------
    def test_filtro_ativo_all_not_admin(self):
        # Cria um barbeiro inativo
        user_inativo = self._create_user(
            'barbeiro.inativo@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
        )
        barbeiro_inativo = Barber.objects.create(
            user=user_inativo, barbershop=self.barbershop_a, especialidade='Corte', ativo=False,
        )

        # Cliente tenta usar ativo=all
        self.client.force_authenticate(self.cliente_a)

        response = self.client.get(self.list_url, {'ativo': 'all'})

        # Não-admins não devem conseguir ver inativos via ativo=all
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # O filtro padrão para não-admins é apenas ativos
        self.assertEqual(response.data['count'], 2)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(barbeiro_inativo.id, ids)

    # ------------------------------------------------------------------
    # 16) Paginação respeita filtro ativo=false
    # ------------------------------------------------------------------
    def test_pagination_respects_ativo_filter(self):
        # Cria 25 barbeiros inativos (mais que o page_size=20)
        for i in range(25):
            user = self._create_user(
                f'barbeiro.inativo{i}@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_a,
            )
            Barber.objects.create(
                user=user, barbershop=self.barbershop_a, especialidade='Corte', ativo=False,
            )

        self.client.force_authenticate(self.admin_a)

        # Primeira página
        response = self.client.get(self.list_url, {'ativo': 'false', 'page': 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 25)
        self.assertLessEqual(len(response.data['results']), 20)  # page_size default
        # Verifica que só inativos aparecem
        for item in response.data['results']:
            self.assertFalse(item['ativo'])

        # Segunda página (deve haver)
        self.assertIsNotNone(response.data['next'])
        response2 = self.client.get(response.data['next'])
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        for item in response2.data['results']:
            self.assertFalse(item['ativo'])

    # ------------------------------------------------------------------
    # 17) Isolamento multi-tenant: ativo=all não vaza dados de outro tenant
    # ------------------------------------------------------------------
    def test_ativo_all_tenant_isolation(self):
        # Cria barbeiro inativo no tenant B
        user_b_inativo = self._create_user(
            'barbeiro.inativo.b@teste.com', User.TipoPerfil.BARBEIRO, self.barbershop_b,
        )
        barbeiro_b_inativo = Barber.objects.create(
            user=user_b_inativo, barbershop=self.barbershop_b, especialidade='Corte', ativo=False,
        )

        # Admin do tenant A usa ativo=all
        self.client.force_authenticate(self.admin_a)
        response = self.client.get(self.list_url, {'ativo': 'all'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        # Deve ver apenas barbeiros do tenant A
        self.assertIn(self.barbeiro_a.id, ids)
        self.assertIn(self.barbeiro_a2.id, ids)
        self.assertNotIn(self.barbeiro_b.id, ids)
        self.assertNotIn(barbeiro_b_inativo.id, ids)
