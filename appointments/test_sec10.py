"""
SEC-10: `exclude_appointment_id` não pode revelar agendamentos de outra barbearia.

O parâmetro, usado na remarcação para tirar o próprio horário da ocupação em
`GET /appointments/available-slots/`, era buscado com
`Appointment.objects.get(pk=...)`, sem condição de barbearia: o registro alheio
(com cliente, barbeiro, serviço e barbearia, por JOIN) era lido antes da
recusa, e a resposta dizia "não pertence à sua barbearia" para o de outra
barbearia e "não encontrado" para um inexistente (MT-AV-02).

Estes testes exigem que o ID de outra barbearia se comporte exatamente como um
inexistente (status, corpo, disponibilidade e consultas SQL), que o registro
alheio nunca seja lido, e que a remarcação legítima continue funcionando.
"""
import re
from datetime import time, timedelta

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service

from .models import Appointment

SENHA = 'Senha-segura-123'
INEXISTENTE = 999999
NAO_ENCONTRADO = {'detail': 'Agendamento a excluir não encontrado.'}
URL = '/api/v1/appointments/available-slots/'


def sql_normalizado(consultas):
    """Consultas do pedido sem os números, para comparar a forma do SQL entre dois IDs."""
    return [re.sub(r'\d+', '<n>', c['sql']) for c in consultas]


class CenarioSec10(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dez = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        cls.t = {'A': cls.criar_tenant('Alfa'), 'B': cls.criar_tenant('Beta')}
        cls.sem = User.objects.create_user(email='publico@sem.test', nome='Conta Publica', password=SENHA)
        cls.superusuario = User.objects.create_superuser(email='operador@plataforma.test', nome='Operador', password=SENHA)

    @classmethod
    def criar_tenant(cls, nome):
        dominio = f'{nome.lower()}.test'
        shop = Barbershop.objects.create(
            nome=f'Barbearia {nome}', endereco='Rua', telefone='11999999999', email=f'contato@{dominio}',
            horario_abertura=time(8), horario_fechamento=time(18),
        )

        def usuario(papel, rotulo):
            return User.objects.create_user(
                email=f'{rotulo}@{dominio}', nome=f'{rotulo} {nome}', password=SENHA, tipo_perfil=papel, barbershop=shop,
            )

        t = type('Tenant', (), {})()
        t.chave, t.nome, t.shop = nome[0], nome, shop
        t.admin = usuario('admin', 'admin')
        t.cliente = usuario('cliente', 'cliente')
        t.cliente2 = usuario('cliente', 'cliente2')
        t.barbeiro = Barber.objects.create(user=usuario('barbeiro', 'barbeiro'), barbershop=shop)
        t.barbeiro2 = Barber.objects.create(user=usuario('barbeiro', 'barbeiro2'), barbershop=shop)
        t.servico = Service.objects.create(barbershop=shop, nome=f'Corte {nome}', preco='50.00', duracao=30)
        t.servico_longo = Service.objects.create(barbershop=shop, nome=f'Combo {nome}', preco='90.00', duracao=60)
        # O horário do cliente às 10:00 com o barbeiro, e outro cliente às 11:00 com o mesmo barbeiro.
        t.agendamento = cls.agendar(t, t.cliente, t.barbeiro, cls.dez)
        t.outro_do_tenant = cls.agendar(t, t.cliente2, t.barbeiro, cls.dez + timedelta(hours=1))
        t.usuarios = {'cliente': t.cliente, 'barbeiro': t.barbeiro.user, 'admin': t.admin}
        return t

    @staticmethod
    def agendar(t, cliente, barbeiro, quando):
        return Appointment.objects.create(
            barbershop=t.shop, cliente=cliente, barbeiro=barbeiro, servico=t.servico, data_hora=quando, preco_historico='50.00',
        )

    def setUp(self):
        cache.clear()

    def outro(self, t):
        return self.t['B' if t.chave == 'A' else 'A']

    @staticmethod
    def como(usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def params(self, t, exclude=None, servico=None):
        dados = {'barbeiro': t.barbeiro.pk, 'servico': (servico or t.servico).pk, 'data': self.dez.date().isoformat()}
        if exclude is not None:
            dados['exclude_appointment_id'] = exclude
        return dados

    def pedir(self, usuario, params):
        with CaptureQueriesContext(connection) as consultas:
            resposta = self.como(usuario).get(URL, params)
        return resposta, consultas.captured_queries

    @staticmethod
    def fotografia():
        return list(Appointment.objects.order_by('pk').values())

    def assert_sem_leitura_do_agendamento(self, consultas, agendamento):
        """Nenhuma consulta busca o agendamento alheio pelo ID sem condição de barbearia."""
        padrao = re.compile(rf'"appointments_appointment"\."id" = {agendamento.pk}\b')
        for consulta in consultas:
            sql = consulta['sql']
            if padrao.search(sql):
                onde = sql.split(' WHERE ', 1)[1]
                self.assertRegex(onde, r'"appointments_appointment"\."barbershop_id" = \d+', sql)
                self.assertNotRegex(onde, rf'"appointments_appointment"\."barbershop_id" = {agendamento.barbershop_id}\b', sql)


class EquivalenciaTests(CenarioSec10):
    """Casos 2, 3, 6, 7 e 8: ID de outra barbearia = ID inexistente, para cada papel, nos dois sentidos."""

    def conferir(self):
        antes = self.fotografia()
        for chave, t in self.t.items():
            alheio = self.outro(t).agendamento
            for papel, usuario in t.usuarios.items():
                with self.subTest(origem=chave, papel=papel):
                    r_alheio, sql_alheio = self.pedir(usuario, self.params(t, alheio.pk))
                    r_inexistente, sql_inexistente = self.pedir(usuario, self.params(t, INEXISTENTE))
                    self.assertEqual(r_alheio.status_code, 404)
                    self.assertEqual(r_alheio.json(), NAO_ENCONTRADO)
                    self.assertEqual((r_alheio.status_code, r_alheio.content), (r_inexistente.status_code, r_inexistente.content))
                    self.assertNotIn('slots', r_alheio.json())
                    self.assertNotIn(self.outro(t).nome.lower(), r_alheio.content.decode().lower())
                    # Mesmas consultas, só mudando o número do ID; e o registro alheio não é lido.
                    self.assertEqual(sql_normalizado(sql_alheio), sql_normalizado(sql_inexistente))
                    self.assert_sem_leitura_do_agendamento(sql_alheio, alheio)
        self.assertEqual(self.fotografia(), antes)

    @override_settings(DEBUG=False)
    def test_id_de_outra_barbearia_igual_a_inexistente(self):
        self.conferir()

    @override_settings(DEBUG=True)
    def test_id_de_outra_barbearia_igual_a_inexistente_debug(self):
        with self.assertLogs('django.request', level='WARNING'):
            self.conferir()

    def test_consulta_do_excluido_ja_tem_condicao_de_barbearia(self):
        t = self.t['A']
        _, consultas = self.pedir(t.cliente, self.params(t, self.t['B'].agendamento.pk))
        busca = [c['sql'] for c in consultas if re.search(r'"appointments_appointment"\."id" = \d+', c['sql'])]
        self.assertEqual(len(busca), 1, busca)
        self.assertIn(f'"appointments_appointment"."barbershop_id" = {t.shop.pk}', busca[0])
        # O agendamento a excluir não é carregado com cliente, barbeiro, serviço ou barbearia por JOIN.
        self.assertNotIn('JOIN', busca[0])


class ParametroTests(CenarioSec10):
    """Casos 1, 4 e 5: próprio, omitido e malformado."""

    def test_proprio_agendamento_e_excluido_da_ocupacao(self):
        for chave, t in self.t.items():
            for papel, usuario in t.usuarios.items():
                with self.subTest(origem=chave, papel=papel):
                    sem_exclusao, _ = self.pedir(usuario, self.params(t))
                    com_exclusao, _ = self.pedir(usuario, self.params(t, t.agendamento.pk))
                    self.assertEqual((sem_exclusao.status_code, com_exclusao.status_code), (200, 200))
                    self.assertNotIn('10:00', sem_exclusao.json()['slots'])
                    self.assertIn('10:00', com_exclusao.json()['slots'])
                    # O horário de outro cliente (11:00) continua ocupado.
                    self.assertNotIn('11:00', com_exclusao.json()['slots'])

    def test_parametro_omitido_ou_vazio_mantem_a_ocupacao(self):
        t = self.t['A']
        omitido, _ = self.pedir(t.cliente, self.params(t))
        vazio, _ = self.pedir(t.cliente, self.params(t, ''))
        self.assertEqual(omitido.status_code, 200)
        self.assertEqual(omitido.content, vazio.content)
        self.assertNotIn('10:00', omitido.json()['slots'])

    def test_valor_malformado_responde_como_inexistente(self):
        t = self.t['A']
        inexistente, _ = self.pedir(t.cliente, self.params(t, INEXISTENTE))
        for valor in ('abc', '1.5', '-1', '0', '1e3', ' ', '99999999999999999999'):
            with self.subTest(valor=valor):
                resposta, consultas = self.pedir(t.cliente, self.params(t, valor))
                self.assertEqual((resposta.status_code, resposta.content), (inexistente.status_code, inexistente.content))
                self.assert_sem_leitura_do_agendamento(consultas, self.t['B'].agendamento)


class PapeisEContextoTests(CenarioSec10):
    """Casos 9 e 10, e as regras atuais dentro da própria barbearia."""

    def test_usuario_sem_barbearia_continua_recusado_antes_de_tudo(self):
        respostas = set()
        for valor in (self.t['A'].agendamento.pk, self.t['B'].agendamento.pk, INEXISTENTE, None):
            resposta, consultas = self.pedir(self.sem, self.params(self.t['B'], valor))
            respostas.add((resposta.status_code, resposta.content))
            self.assertEqual(consultas, [])
        self.assertEqual(respostas, {(403, b'{"detail":"Usu\xc3\xa1rio sem barbearia vinculada."}')})

    def test_superusuario_mantem_as_regras_atuais(self):
        # Sem barbearia: recusado como antes (a ação usa a barbearia do usuário).
        resposta, _ = self.pedir(self.superusuario, self.params(self.t['A'], self.t['A'].agendamento.pk))
        self.assertEqual(resposta.status_code, 403)
        # Com barbearia (A): exclui o de A e trata o de B como inexistente, sem ampliar o escopo.
        su = User.objects.create_superuser(email='su-a@plataforma.test', nome='SU A', password=SENHA)
        su.barbershop = self.t['A'].shop
        su.save(update_fields=['barbershop'])
        proprio, _ = self.pedir(su, self.params(self.t['A'], self.t['A'].agendamento.pk))
        self.assertIn('10:00', proprio.json()['slots'])
        alheio, sql_alheio = self.pedir(su, self.params(self.t['A'], self.t['B'].agendamento.pk))
        inexistente, _ = self.pedir(su, self.params(self.t['A'], INEXISTENTE))
        self.assertEqual((alheio.status_code, alheio.content), (inexistente.status_code, inexistente.content))
        self.assert_sem_leitura_do_agendamento(sql_alheio, self.t['B'].agendamento)

    def test_regras_atuais_dentro_da_propria_barbearia(self):
        """Inalteradas: o cliente só exclui o próprio horário; o barbeiro, a própria agenda; o status precisa permitir."""
        t = self.t['A']
        resposta, _ = self.pedir(t.cliente, self.params(t, t.outro_do_tenant.pk))
        self.assertEqual(resposta.status_code, 403)
        outro_barbeiro = self.agendar(t, t.cliente2, t.barbeiro2, self.dez + timedelta(hours=2))
        resposta, _ = self.pedir(t.barbeiro.user, self.params(t, outro_barbeiro.pk))
        self.assertEqual(resposta.status_code, 403)
        # O admin pode excluir qualquer horário da barbearia (ex.: remarcar por telefone).
        resposta, _ = self.pedir(t.admin, self.params(t, t.outro_do_tenant.pk))
        self.assertIn('11:00', resposta.json()['slots'])
        Appointment.objects.filter(pk=t.outro_do_tenant.pk).update(status=Appointment.Status.CANCELADO)
        resposta, _ = self.pedir(t.admin, self.params(t, t.outro_do_tenant.pk))
        self.assertEqual(resposta.status_code, 400)


class RemarcacaoTests(CenarioSec10):
    """Casos 11 e 12: remarcação legítima e conflitos dentro da mesma barbearia."""

    def test_remarcacao_legitima_com_horario_que_so_aparece_ao_excluir_o_proprio(self):
        t = self.t['A']
        api = self.como(t.cliente)
        # Trocar para o combo de 60 min no mesmo horário (10:00-11:00): ele sobrepõe o próprio
        # horário das 10:00, então só aparece excluindo-o. A grade usa passo igual à duração.
        sem_exclusao = api.get(URL, self.params(t, servico=t.servico_longo)).json()['slots']
        com_exclusao = api.get(URL, self.params(t, t.agendamento.pk, servico=t.servico_longo)).json()['slots']
        self.assertNotIn('10:00', sem_exclusao)
        self.assertIn('10:00', com_exclusao)
        nova = self.dez
        resposta = api.patch(
            f'/api/v1/appointments/{t.agendamento.pk}/',
            {'servico': t.servico_longo.pk, 'data_hora': nova.isoformat()}, format='json',
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)
        t.agendamento.refresh_from_db()
        self.assertEqual((t.agendamento.servico_id, timezone.localtime(t.agendamento.data_hora)), (t.servico_longo.pk, nova))

    def test_conflitos_da_mesma_barbearia_continuam_valendo(self):
        t = self.t['A']
        api = self.como(t.cliente)
        # Excluir o próprio horário não libera o das 11:00 (outro cliente, mesmo barbeiro)...
        slots = api.get(URL, self.params(t, t.agendamento.pk, servico=t.servico_longo)).json()['slots']
        self.assertIn('10:00', slots)
        self.assertNotIn('11:00', slots)
        # ...e a remarcação para cima dele é recusada.
        resposta = api.patch(
            f'/api/v1/appointments/{t.agendamento.pk}/',
            {'data_hora': (self.dez + timedelta(hours=1)).isoformat()}, format='json',
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'data_hora': ['Este barbeiro já possui um agendamento neste horário.']})
        # Para outro barbeiro, o próprio horário (que não está na agenda dele) é ignorado.
        outro = self.agendar(t, t.cliente2, t.barbeiro2, self.dez)
        slots = api.get(URL, {**self.params(t, t.agendamento.pk), 'barbeiro': t.barbeiro2.pk}).json()['slots']
        self.assertNotIn('10:00', slots)
        self.assertEqual(Appointment.objects.get(pk=outro.pk).status, Appointment.Status.AGENDADO)
