"""
Testes das correções de prioridade ALTA da auditoria ligadas a accounts:

* mudança de papel mantendo o perfil `Barber` consistente;
* rate limiting (throttling) em login e cadastro público.
"""
from datetime import time

from unittest import mock

from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from barbershops.models import Barber, Barbershop

from .models import User


class TransicaoDePapelTests(APITestCase):
    """
    ALTO — antes, mudar `tipo_perfil` por PATCH /users/{id}/ deixava o
    sistema inconsistente nos dois sentidos (barbeiro sem perfil → HTTP 500;
    ex-barbeiro com perfil ativo e ainda agendável).
    """

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = self.criar_usuario('admin@example.com', User.TipoPerfil.ADMIN)
        self.barbeiro_user = self.criar_usuario(
            'barbeiro@example.com', User.TipoPerfil.BARBEIRO
        )
        self.barbeiro = Barber.objects.create(
            user=self.barbeiro_user, barbershop=self.barbershop
        )
        self.client.force_authenticate(self.admin)

    def criar_usuario(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def test_rebaixar_barbeiro_desativa_o_perfil_de_barbeiro(self):
        resposta = self.client.patch(
            reverse('user-detail', args=[self.barbeiro_user.pk]),
            {'tipo_perfil': 'cliente'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.barbeiro.refresh_from_db()
        self.assertFalse(
            self.barbeiro.ativo,
            'O perfil de barbeiro continuou ativo e agendável após o rebaixamento.',
        )

    def test_promover_de_volta_reativa_o_perfil_existente(self):
        self.barbeiro.ativo = False
        self.barbeiro.save(update_fields=['ativo'])
        self.barbeiro_user.tipo_perfil = User.TipoPerfil.CLIENTE
        self.barbeiro_user.save(update_fields=['tipo_perfil'])

        resposta = self.client.patch(
            reverse('user-detail', args=[self.barbeiro_user.pk]),
            {'tipo_perfil': 'barbeiro'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.barbeiro.refresh_from_db()
        self.assertTrue(self.barbeiro.ativo)

    def test_promover_sem_perfil_cria_perfil(self):
        """Ao promover um usuário a barbeiro, criar o perfil profissional se não existir."""
        cliente = self.criar_usuario('cliente@example.com', User.TipoPerfil.CLIENTE)
        resposta = self.client.patch(
            reverse('user-detail', args=[cliente.pk]),
            {'tipo_perfil': 'barbeiro'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.tipo_perfil, User.TipoPerfil.BARBEIRO)
        # Check that a barber profile exists and is active
        from barbershops.models import Barber
        barber = Barber.objects.get(user=cliente)
        self.assertTrue(barber.ativo)


class ThrottlingTests(APITestCase):
    """
    ALTO — /auth/login/ e /auth/register/ não tinham nenhum limite de
    requisições: força bruta de senha e criação massiva de contas eram
    livres. Os limites reais ficam em settings (configuráveis por .env);
    aqui usamos taxas mínimas só para provar que o bloqueio existe.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        # `throttle_classes` e `THROTTLE_RATES` do DRF são atributos de
        # classe resolvidos no import, então @override_settings não os
        # alcança: aplicamos os limites diretamente, só nestes testes.
        patches = [
            mock.patch.object(APIView, 'throttle_classes', [ScopedRateThrottle]),
            mock.patch.object(
                SimpleRateThrottle, 'THROTTLE_RATES',
                # 'register_day' (TEN-03, mitigação D) é o limite diário do
                # cadastro: fica alto aqui para o bloqueio continuar vindo do
                # 'register', que é o que este teste verifica.
                {'login': '2/min', 'register': '2/min', 'register_day': '1000/day'},
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_login_bloqueia_apos_o_limite(self):
        url = reverse('token_obtain_pair')
        payload = {'email': 'ninguem@example.com', 'password': 'errada'}
        codigos = [self.client.post(url, payload, format='json').status_code
                   for _ in range(3)]
        self.assertEqual(codigos[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_cadastro_publico_bloqueia_apos_o_limite(self):
        url = reverse('auth-register')
        codigos = []
        for indice in range(3):
            codigos.append(self.client.post(url, {
                'email': f'novo{indice}@example.com',
                'nome': 'Novo Usuário',
                'password': 'Senha-segura-123',
            }, format='json').status_code)
        self.assertEqual(codigos[-1], status.HTTP_429_TOO_MANY_REQUESTS)
