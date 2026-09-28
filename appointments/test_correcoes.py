"""
Testes das correções CRÍTICAS e de prioridade ALTA da auditoria técnica.

Cobertura deste módulo:

* condição de corrida em agendamentos (duas requisições simultâneas para o
  mesmo barbeiro/horário) — CRÍTICO;
* permissões granulares em AppointmentViewSet (quem exclui, quem muda o
  status) — ALTO;
* usuário com `tipo_perfil='barbeiro'` sem perfil `Barber` (antes: HTTP 500
  no filtro multi-tenant) — ALTO;
* exclusão de barbeiro/serviço com histórico de agendamentos (antes: apagava
  o histórico em cascata) — ALTO;
* confirmação obrigatória para excluir uma barbearia inteira — CRÍTICO.
"""
from datetime import time, timedelta

from unittest import skipUnless

from django.db import connection, connections
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment


class BaseAgendaSetup:
    """Cenário compartilhado: uma barbearia com admin, cliente, barbeiro e serviço."""

    def montar_cenario(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = self.criar_usuario('admin@example.com', User.TipoPerfil.ADMIN)
        self.cliente = self.criar_usuario('cliente@example.com', User.TipoPerfil.CLIENTE)
        self.barbeiro_user = self.criar_usuario(
            'barbeiro@example.com', User.TipoPerfil.BARBEIRO
        )
        self.barbeiro = Barber.objects.create(
            user=self.barbeiro_user, barbershop=self.barbershop
        )
        self.servico = Service.objects.create(
            barbershop=self.barbershop, nome='Corte', preco='50.00', duracao=30,
        )
        # Amanhã às 10h locais: dentro do horário de funcionamento e no futuro.
        amanha = (timezone.localtime() + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.horario = amanha

    def criar_usuario(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def payload(self, data_hora=None):
        return {
            'cliente': self.cliente.pk,
            'barbeiro': self.barbeiro.pk,
            'servico': self.servico.pk,
            'data_hora': (data_hora or self.horario).isoformat(),
        }

    def criar_agendamento(self, data_hora=None, **kwargs):
        dados = {
            'barbershop': self.barbershop,
            'cliente': self.cliente,
            'barbeiro': self.barbeiro,
            'servico': self.servico,
            'data_hora': data_hora or self.horario,
        }
        dados.update(kwargs)
        return Appointment.objects.create(**dados)


@skipUnless(
    connection.features.has_select_for_update,
    'O teste de concorrência exige um banco com SELECT FOR UPDATE (PostgreSQL).',
)
class AppointmentConcorrenciaTests(BaseAgendaSetup, TransactionTestCase):
    """
    CRÍTICO — condição de corrida (overbooking).

    Problema: a checagem de conflito roda em `full_clean()`, antes do save e
    sem transação/lock. Duas requisições simultâneas para o mesmo barbeiro e
    horário passavam as duas na validação (nenhuma enxergava o registro da
    outra) e as duas eram gravadas.

    Correção: `AppointmentViewSet.create/update` envolvem validação + save em
    `transaction.atomic()` e travam a linha do barbeiro com
    `select_for_update()`, serializando as tentativas concorrentes.

    Usa TransactionTestCase (e não TestCase) porque cada thread precisa de
    uma transação real e visível às demais.
    """

    # TransactionTestCase trunca as tabelas entre testes; sem isso o
    # sequence de ids e as threads não enxergam os dados corretamente.
    reset_sequences = True

    def setUp(self):
        self.montar_cenario()

    def _post_em_thread(self, resultados, indice):
        client = APIClient()
        client.force_authenticate(self.cliente)
        try:
            resposta = client.post(
                reverse('appointment-list'), self.payload(), format='json'
            )
            resultados[indice] = resposta.status_code
        finally:
            # Cada thread abre sua própria conexão; fechar evita conexões
            # penduradas ao fim do teste.
            connections.close_all()

    def test_duas_requisicoes_simultaneas_geram_apenas_um_agendamento(self):
        import threading

        resultados = [None, None]
        threads = [
            threading.Thread(target=self._post_em_thread, args=(resultados, i))
            for i in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(
            Appointment.objects.filter(barbeiro=self.barbeiro).count(),
            1,
            f'Overbooking: as duas requisições foram gravadas ({resultados}).',
        )
        self.assertIn(status.HTTP_201_CREATED, resultados)
        self.assertIn(status.HTTP_400_BAD_REQUEST, resultados)


class AppointmentPermissoesTests(BaseAgendaSetup, APITestCase):
    """ALTO — AppointmentViewSet era o único ViewSet sem permissão granular."""

    def setUp(self):
        self.montar_cenario()
        self.agendamento = self.criar_agendamento()

    def test_cliente_pode_cancelar_o_proprio_agendamento_por_delete(self):
        self.client.force_authenticate(self.cliente)
        resposta = self.client.delete(
            reverse('appointment-detail', args=[self.agendamento.pk])
        )
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Appointment.Status.CANCELADO)
        self.assertTrue(Appointment.objects.filter(pk=self.agendamento.pk).exists())

    def test_barbeiro_nao_pode_excluir_agendamento(self):
        self.client.force_authenticate(self.barbeiro_user)
        resposta = self.client.delete(
            reverse('appointment-detail', args=[self.agendamento.pk])
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_ainda_pode_excluir_agendamento(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.delete(
            reverse('appointment-detail', args=[self.agendamento.pk])
        )
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)

    def test_cliente_pode_cancelar_o_proprio_agendamento(self):
        """Compatibilidade com o frontend: cancelar é PATCH status=cancelado."""
        self.client.force_authenticate(self.cliente)
        resposta = self.client.patch(
            reverse('appointment-detail', args=[self.agendamento.pk]),
            {'status': 'cancelado'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Appointment.Status.CANCELADO)

    def test_cliente_nao_pode_marcar_como_realizado(self):
        self.client.force_authenticate(self.cliente)
        resposta = self.client.patch(
            reverse('appointment-detail', args=[self.agendamento.pk]),
            {'status': 'realizado'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Appointment.Status.AGENDADO)

    def test_barbeiro_pode_confirmar_e_realizar(self):
        self.client.force_authenticate(self.barbeiro_user)
        for novo_status in ('confirmado', 'realizado'):
            resposta = self.client.patch(
                reverse('appointment-detail', args=[self.agendamento.pk]),
                {'status': novo_status},
                format='json',
            )
            self.assertEqual(resposta.status_code, status.HTTP_200_OK, novo_status)


class BarbeiroSemPerfilTests(BaseAgendaSetup, APITestCase):
    """
    ALTO — usuário com papel `barbeiro` mas sem registro `Barber`.

    Antes, o filtro multi-tenant acessava `user.perfil_barbeiro` direto e
    estourava `RelatedObjectDoesNotExist` → HTTP 500 em /barbers/,
    /services/ e /appointments/.
    """

    def setUp(self):
        self.montar_cenario()
        # Promovido a barbeiro sem que o perfil profissional exista.
        self.sem_perfil = self.criar_usuario('novo@example.com', User.TipoPerfil.CLIENTE)
        self.sem_perfil.tipo_perfil = User.TipoPerfil.BARBEIRO
        self.sem_perfil.save(update_fields=['tipo_perfil'])
        self.client.force_authenticate(self.sem_perfil)

    def test_listagens_respondem_200_vazio_em_vez_de_500(self):
        for rota in ('barber-list', 'service-list', 'appointment-list'):
            with self.subTest(rota=rota):
                resposta = self.client.get(reverse(rota))
                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertEqual(resposta.data['results'], [])

    def test_criar_agendamento_sem_tenant_retorna_403(self):
        resposta = self.client.post(
            reverse('appointment-list'), self.payload(), format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


class ExclusaoComHistoricoTests(BaseAgendaSetup, APITestCase):
    """ALTO/CRÍTICO — exclusões que apagavam histórico em cascata."""

    def setUp(self):
        self.montar_cenario()
        self.agendamento = self.criar_agendamento(
            status=Appointment.Status.REALIZADO
        )
        self.client.force_authenticate(self.admin)

    def test_excluir_barbeiro_com_agendamentos_retorna_204(self):
        resposta = self.client.delete(reverse('barber-detail', args=[self.barbeiro.pk]))
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        # Verifica que o barbeiro foi desativado (soft delete)
        self.barbeiro.refresh_from_db()
        self.assertFalse(self.barbeiro.ativo)
        self.assertIsNotNone(self.barbeiro.deleted_at)
        self.assertIsNotNone(self.barbeiro.deleted_by)
        # Verifica que os agendamentos históricos foram preservados
        self.assertTrue(Appointment.objects.filter(pk=self.agendamento.pk).exists())
        self.assertTrue(Barber.objects.filter(pk=self.barbeiro.pk).exists())

    def test_excluir_servico_com_agendamentos_retorna_204(self):
        resposta = self.client.delete(reverse('service-detail', args=[self.servico.pk]))
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        # Verifica que o serviço foi desativado (soft delete)
        self.servico.refresh_from_db()
        self.assertFalse(self.servico.ativo)
        self.assertIsNotNone(self.servico.deleted_at)
        self.assertIsNotNone(self.servico.deleted_by)
        # Verifica que os agendamentos históricos foram preservados
        self.assertTrue(Appointment.objects.filter(pk=self.agendamento.pk).exists())

    def test_excluir_servico_sem_agendamentos_continua_funcionando(self):
        outro = Service.objects.create(
            barbershop=self.barbershop, nome='Barba', preco='30.00', duracao=20,
        )
        resposta = self.client.delete(reverse('service-detail', args=[outro.pk]))
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)

    def test_excluir_barbearia_exige_confirmacao(self):
        staff = User.objects.create_user(
            email='plataforma@example.com',
            nome='Equipe',
            password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop,
            is_staff=True,
        )
        self.client.force_authenticate(staff)
        url = reverse('barbershop-detail', args=[self.barbershop.pk])

        sem_confirmacao = self.client.delete(url)
        self.assertEqual(sem_confirmacao.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Barbershop.objects.filter(pk=self.barbershop.pk).exists())

        confirmacao_errada = self.client.delete(f'{url}?confirmar=Outro Nome')
        self.assertEqual(confirmacao_errada.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Barbershop.objects.filter(pk=self.barbershop.pk).exists())

        correta = self.client.delete(f'{url}?confirmar={self.barbershop.nome}')
        self.assertEqual(correta.status_code, status.HTTP_204_NO_CONTENT)
        self.barbershop.refresh_from_db()
        self.assertFalse(self.barbershop.ativo)
