from django.test import TestCase

"""
Testes automatizados do app services.

Cobre (ver plano discutido em conversa): permissões por perfil
(admin/barbeiro/cliente), isolamento multi-tenant, proteção contra o
cliente informar `barbershop` na criação, filtro por `ativo`, e
validação de dados (duração e preço).

IMPORTANTE: os testes `test_duracao_zero_rejeitada` e
`test_preco_negativo_rejeitado` descrevem o comportamento DESEJADO
(zero/negativo deveriam ser rejeitados com 400) e falham propositalmente
contra a implementação atual:
- `Service.duracao` é PositiveIntegerField, que só rejeita negativos
  (DRF gera `min_value=0`, então 0 passa).
- `Service.preco` é DecimalField sem nenhum validador de valor mínimo.
Ficam aqui como regressão documentada, sem alterar services/models.py
ou services/serializers.py nesta etapa.
"""
from datetime import time
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service


class ServiceAPITestCase(APITestCase):
    """Fixtures compartilhadas: duas barbearias (tenants), um usuário de
    cada perfil na barbearia A (+ o profissional Barber do barbeiro),
    um admin na barbearia B só para os testes cross-tenant, e um
    serviço já existente em cada barbearia."""

    def setUp(self):
        # --- duas barbearias (tenants) ---
        self.barbershop_a = Barbershop.objects.create(
            nome='Barbearia A',
            endereco='Rua A, 1',
            telefone='11900000001',
            email='contato@barbeariaa.com',
            horario_abertura=time(9, 0),
            horario_fechamento=time(19, 0),
        )
        self.barbershop_b = Barbershop.objects.create(
            nome='Barbearia B',
            endereco='Rua B, 2',
            telefone='11900000002',
            email='contato@barbeariab.com',
            horario_abertura=time(9, 0),
            horario_fechamento=time(19, 0),
        )

        # --- usuários da barbearia A, um de cada perfil ---
        self.admin_a = User.objects.create_user(
            email='admin.a@teste.com', nome='Admin A', password='SenhaForte123',
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=self.barbershop_a,
        )
        self.cliente_a = User.objects.create_user(
            email='cliente.a@teste.com', nome='Cliente A', password='SenhaForte123',
            tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=self.barbershop_a,
        )
        self.barbeiro_user_a = User.objects.create_user(
            email='barbeiro.a@teste.com', nome='Barbeiro A', password='SenhaForte123',
            tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=self.barbershop_a,
        )
        self.barbeiro_a = Barber.objects.create(
            user=self.barbeiro_user_a, barbershop=self.barbershop_a,
        )

        # --- usuário da barbearia B, só para os testes cross-tenant ---
        self.admin_b = User.objects.create_user(
            email='admin.b@teste.com', nome='Admin B', password='SenhaForte123',
            tipo_perfil=User.TipoPerfil.ADMIN, barbershop=self.barbershop_b,
        )

        # --- um serviço já existente em cada barbearia ---
        self.servico_a = Service.objects.create(
            barbershop=self.barbershop_a, nome='Corte Simples',
            descricao='Corte tradicional', preco=Decimal('35.00'),
            duracao=30, ativo=True,
        )
        self.servico_b = Service.objects.create(
            barbershop=self.barbershop_b, nome='Corte Simples B',
            descricao='Corte tradicional', preco=Decimal('40.00'),
            duracao=30, ativo=True,
        )

        self.list_url = '/api/v1/services/'

    # ---- helpers ----

    def _detail_url(self, service_id):
        return f'/api/v1/services/{service_id}/'

    def _valid_payload(self, **overrides):
        payload = {
            'nome': 'Corte + Barba',
            'descricao': 'Combo completo',
            'preco': '55.00',
            'duracao': 45,
            'ativo': True,
        }
        payload.update(overrides)
        return payload

    # ------------------------------------------------------------------
    # 1) Admin consegue criar serviço
    # ------------------------------------------------------------------
    def test_admin_can_create_service(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post(self.list_url, self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Service.objects.get(pk=response.data['id'])
        self.assertEqual(novo.barbershop_id, self.barbershop_a.id)
        self.assertEqual(novo.nome, 'Corte + Barba')

    # ------------------------------------------------------------------
    # 2) Admin consegue editar serviço
    # ------------------------------------------------------------------
    def test_admin_can_update_service(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.patch(
            self._detail_url(self.servico_a.id),
            {'nome': 'Corte Premium', 'preco': '50.00'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.servico_a.refresh_from_db()
        self.assertEqual(self.servico_a.nome, 'Corte Premium')
        self.assertEqual(self.servico_a.preco, Decimal('50.00'))

    # ------------------------------------------------------------------
    # 3) Admin consegue excluir serviço (soft delete)
    # ------------------------------------------------------------------
    def test_admin_can_delete_service(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.delete(self._detail_url(self.servico_a.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verifica soft delete: serviço marcado como inativo, não excluído fisicamente
        self.servico_a.refresh_from_db()
        self.assertFalse(self.servico_a.ativo)
        # Ainda existe no banco, mas está inativo
        self.assertTrue(Service.objects.filter(pk=self.servico_a.id).exists())

    # ------------------------------------------------------------------
    # 4) Cliente consegue listar serviços da própria barbearia
    # ------------------------------------------------------------------
    def test_cliente_can_list_own_barbershop_services(self):
        self.client.force_authenticate(user=self.cliente_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.servico_a.id, ids)
        self.assertNotIn(self.servico_b.id, ids)

    # ------------------------------------------------------------------
    # 5) Barbeiro consegue listar serviços da própria barbearia
    # ------------------------------------------------------------------
    def test_barbeiro_can_list_own_barbershop_services(self):
        self.client.force_authenticate(user=self.barbeiro_user_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.servico_a.id, ids)
        self.assertNotIn(self.servico_b.id, ids)

    # ------------------------------------------------------------------
    # 6) Cliente não consegue criar serviço
    # ------------------------------------------------------------------
    def test_cliente_cannot_create_service(self):
        self.client.force_authenticate(user=self.cliente_a)
        antes = Service.objects.count()
        response = self.client.post(self.list_url, self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Service.objects.count(), antes)

    # ------------------------------------------------------------------
    # 7) Barbeiro não consegue criar serviço
    # ------------------------------------------------------------------
    def test_barbeiro_cannot_create_service(self):
        self.client.force_authenticate(user=self.barbeiro_user_a)
        antes = Service.objects.count()
        response = self.client.post(self.list_url, self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Service.objects.count(), antes)

    # ------------------------------------------------------------------
    # 8) Cliente não consegue editar serviço
    # ------------------------------------------------------------------
    def test_cliente_cannot_update_service(self):
        self.client.force_authenticate(user=self.cliente_a)
        response = self.client.patch(
            self._detail_url(self.servico_a.id), {'nome': 'Hackeado'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.servico_a.refresh_from_db()
        self.assertNotEqual(self.servico_a.nome, 'Hackeado')

    # ------------------------------------------------------------------
    # 9) Barbeiro não consegue excluir serviço
    # ------------------------------------------------------------------
    def test_barbeiro_cannot_delete_service(self):
        self.client.force_authenticate(user=self.barbeiro_user_a)
        response = self.client.delete(self._detail_url(self.servico_a.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Service.objects.filter(pk=self.servico_a.id).exists())

    # ------------------------------------------------------------------
    # 10) Usuário de uma barbearia não consegue visualizar serviço de outra
    # ------------------------------------------------------------------
    def test_user_cannot_view_service_from_another_barbershop(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.get(self._detail_url(self.servico_b.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # e também não pode aparecer na listagem
        lista = self.client.get(self.list_url)
        ids = [item['id'] for item in lista.data['results']]
        self.assertNotIn(self.servico_b.id, ids)

    # ------------------------------------------------------------------
    # 11) Usuário não consegue informar barbershop de outra barbearia
    # ------------------------------------------------------------------
    def test_cannot_set_barbershop_on_create(self):
        self.client.force_authenticate(user=self.admin_a)
        payload = self._valid_payload(barbershop=self.barbershop_b.id)
        response = self.client.post(self.list_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Service.objects.get(pk=response.data['id'])
        self.assertEqual(novo.barbershop_id, self.barbershop_a.id)
        self.assertNotEqual(novo.barbershop_id, self.barbershop_b.id)

    # ------------------------------------------------------------------
    # 12a) Duração negativa é rejeitada
    # ------------------------------------------------------------------
    def test_duracao_negativa_rejeitada(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post(
            self.list_url, self._valid_payload(duracao=-10), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('duracao', response.data)

    # ------------------------------------------------------------------
    # 12b) Duração zero é rejeitada
    # ------------------------------------------------------------------
    def test_duracao_zero_rejeitada(self):
        """Espera 400. FALHA HOJE: PositiveIntegerField aceita zero
        (só bloqueia negativos) — ver docstring do módulo."""
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post(
            self.list_url, self._valid_payload(duracao=0), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('duracao', response.data)

    # ------------------------------------------------------------------
    # 13) Preço negativo é rejeitado
    # ------------------------------------------------------------------
    def test_preco_negativo_rejeitado(self):
        """Espera 400. FALHA HOJE: `preco` não tem validador de valor
        mínimo — ver docstring do módulo."""
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post(
            self.list_url, self._valid_payload(preco='-10.00'), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preco', response.data)

    # ------------------------------------------------------------------
    # 14) Filtro ?ativo=true funciona
    # ------------------------------------------------------------------
    def test_filtro_ativo_true(self):
        Service.objects.create(
            barbershop=self.barbershop_a, nome='Promoção Antiga',
            preco=Decimal('20.00'), duracao=20, ativo=False,
        )
        self.client.force_authenticate(user=self.admin_a)

        response = self.client.get(self.list_url, {'ativo': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        nomes = [item['nome'] for item in response.data['results']]
        self.assertIn('Corte Simples', nomes)
        self.assertNotIn('Promoção Antiga', nomes)
