"""
TEN-02: usuário sem barbearia não pode sondar a agenda de outras barbearias.

Na auditoria, uma conta do cadastro público enviava `POST /appointments/` com o
barbeiro e o serviço de outra barbearia. A validação rodava antes da recusa
(que só existia em `perform_create`), o `validate()` pulava as checagens de
barbearia quando `barbershop_id` era vazio, e o `clean()` do model consultava a
agenda do barbeiro. A resposta dizia "Este barbeiro já possui um agendamento
neste horário." só quando o horário estava ocupado: um oráculo de agenda.

A correção estrutural do TEN-01 escondeu o sintoma (os campos relacionais ficam
vazios para quem não tem barbearia), mas o defeito continuava: bastava o escopo
dos campos ser afrouxado para o oráculo voltar. Estes testes exigem que a
recusa aconteça antes de qualquer validação, com uma resposta única, sem
consultar dados de outra barbearia e sem depender do escopo dos campos.
"""
import re
from datetime import time, timedelta
from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from config import tenancy
from services.models import Service

from .models import Appointment
from .serializers import AppointmentSerializer

SENHA = 'Senha-segura-123'
RECUSA = {'detail': 'Usuário sem barbearia vinculada.'}
TABELAS_DE_TENANT = (
    'appointments_appointment', 'barbershops_barber', 'services_service', 'barbershops_barbershop',
)


def tabelas(consulta):
    return set(re.findall(r'(?:FROM|JOIN|UPDATE|INTO) "(\w+)"', consulta['sql']))


def escopo_amplo(*args, **kwargs):
    """Simula uma mudança futura que libere os campos relacionais (ex.: catálogo público)."""
    return tenancy.TODAS_AS_BARBEARIAS


class CenarioTen02(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ocupado = (timezone.localtime() + timedelta(days=2)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        cls.livre = cls.ocupado + timedelta(hours=4)
        cls.a = cls.criar_tenant('Alfa')
        cls.b = cls.criar_tenant('Beta')
        # Conta como a do cadastro público: cliente, sem barbearia.
        cls.sem = User.objects.create_user(email='publico@sem.test', nome='Conta Publica', password=SENHA)
        cls.superusuario = User.objects.create_superuser(
            email='operador@plataforma.test', nome='Operador', password=SENHA,
        )

    @classmethod
    def criar_tenant(cls, nome):
        dominio = f'{nome.lower()}.test'
        shop = Barbershop.objects.create(
            nome=f'Barbearia {nome}', endereco='Rua', telefone='11999999999', email=f'contato@{dominio}',
            horario_abertura=time(8), horario_fechamento=time(18),
        )

        def usuario(papel, rotulo):
            return User.objects.create_user(
                email=f'{rotulo}@{dominio}', nome=f'{rotulo} {nome}', password=SENHA,
                tipo_perfil=papel, barbershop=shop,
            )

        t = type('Tenant', (), {})()
        t.shop = shop
        t.admin = usuario('admin', 'admin')
        t.cliente = usuario('cliente', 'cliente')
        t.barbeiro = Barber.objects.create(user=usuario('barbeiro', 'barbeiro'), barbershop=shop)
        t.servico = Service.objects.create(barbershop=shop, nome=f'Corte {nome}', preco='50.00', duracao=30)
        t.agendamento = Appointment.objects.create(
            barbershop=shop, cliente=t.cliente, barbeiro=t.barbeiro, servico=t.servico,
            data_hora=cls.ocupado, preco_historico='50.00',
        )
        return t

    # -- auxiliares ---------------------------------------------------------

    def setUp(self):
        cache.clear()

    @staticmethod
    def entrar(usuario):
        """Autenticação real (JWT), como o frontend."""
        cache.clear()
        resposta = APIClient().post('/api/v1/auth/login/', {'email': usuario.email, 'password': SENHA}, format='json')
        assert resposta.status_code == 200, resposta.content
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {resposta.json()["access"]}')
        return cliente

    def corpo(self, t, quando, **troca):
        dados = {'cliente': t.cliente.pk, 'barbeiro': t.barbeiro.pk, 'servico': t.servico.pk, 'data_hora': quando.isoformat()}
        dados.update(troca)
        return dados

    def fotografia(self):
        return list(Appointment.objects.order_by('pk').values())

    def assert_sem_leitura_de_tenant(self, consultas, solicitante):
        """Só a autenticação lê o banco: a linha do próprio usuário, e nada de agenda, barbeiro, serviço ou barbearia."""
        for consulta in consultas:
            usadas = tabelas(consulta)
            self.assertFalse(usadas & set(TABELAS_DE_TENANT), consulta['sql'])
            if 'accounts_user' in usadas:
                self.assertRegex(consulta['sql'], rf'"accounts_user"\."id" = {solicitante.pk}\b', consulta['sql'])
                self.assertNotIn('tipo_perfil', consulta['sql'].split(' WHERE ', 1)[-1], consulta['sql'])


class SemBarbeariaTests(CenarioTen02):
    """Casos 1 a 4 do TEN-02 e as demais operações de agendamento."""

    def casos_de_criacao(self):
        b = self.b
        return {
            '1 horário ocupado de B': self.corpo(b, self.ocupado),
            '2 horário livre de B': self.corpo(b, self.livre),
            '3 barbeiro válido de B': self.corpo(b, self.ocupado, cliente=self.sem.pk, servico=999999),
            '4 IDs inexistentes': self.corpo(b, self.ocupado, cliente=999999, barbeiro=999999, servico=999999),
            'corpo vazio': {},
            'data inválida': self.corpo(b, self.ocupado, data_hora='amanhã'),
        }

    def conferir_criacao(self):
        api = self.entrar(self.sem)
        antes = self.fotografia()
        for nome, corpo in self.casos_de_criacao().items():
            with self.subTest(caso=nome):
                with CaptureQueriesContext(connection) as consultas:
                    resposta = api.post('/api/v1/appointments/', corpo, format='json')
                self.assertEqual(resposta.status_code, 403)
                self.assertEqual(resposta.json(), RECUSA)
                self.assertNotIn('data_hora', resposta.content.decode())
                self.assert_sem_leitura_de_tenant(consultas.captured_queries, self.sem)
        self.assertEqual(self.fotografia(), antes)

    @override_settings(DEBUG=False)
    def test_criacao_recusada_antes_da_validacao_com_resposta_unica(self):
        self.conferir_criacao()

    @override_settings(DEBUG=True)
    def test_criacao_recusada_antes_da_validacao_com_resposta_unica_debug(self):
        with self.assertLogs('django.request', level='WARNING'):
            self.conferir_criacao()

    def test_recusa_nao_depende_do_escopo_dos_campos(self):
        """Mesmo se os campos relacionais forem liberados no futuro, a agenda de B não é consultada."""
        api = self.entrar(self.sem)
        respostas = {}
        with mock.patch('config.tenancy.barbearia_do_pedido', side_effect=escopo_amplo):
            for nome, quando in (('ocupado', self.ocupado), ('livre', self.livre)):
                with self.subTest(horario=nome):
                    with CaptureQueriesContext(connection) as consultas:
                        resposta = api.post('/api/v1/appointments/', self.corpo(self.b, quando), format='json')
                    respostas[nome] = (resposta.status_code, resposta.content)
                    self.assertEqual(resposta.status_code, 403)
                    self.assert_sem_leitura_de_tenant(consultas.captured_queries, self.sem)
        self.assertEqual(respostas['ocupado'], respostas['livre'])
        self.assertFalse(Appointment.objects.filter(cliente=self.sem).exists())

    def test_validate_recusa_sem_barbearia_antes_das_regras_de_negocio(self):
        """Segunda camada: o serializer também falha fechado, sem depender da view nem do escopo dos campos."""
        pedido = type('Pedido', (), {'user': self.sem})()
        with mock.patch('config.tenancy.barbearia_do_pedido', side_effect=escopo_amplo):
            serializer = AppointmentSerializer(data=self.corpo(self.b, self.ocupado), context={'request': pedido})
            with CaptureQueriesContext(connection) as consultas:
                with self.assertRaises(PermissionDenied) as recusa:
                    serializer.is_valid()
        self.assertEqual(str(recusa.exception.detail), RECUSA['detail'])
        agenda = [c['sql'] for c in consultas.captured_queries if 'appointments_appointment' in tabelas(c)]
        self.assertEqual(agenda, [])

    def test_demais_operacoes_sem_barbearia_nao_revelam_nada(self):
        api = self.entrar(self.sem)
        antes = self.fotografia()
        b = self.b
        dia_ocupado, dia_livre = self.ocupado.date(), (self.ocupado + timedelta(days=1)).date()
        grupos = {
            'PATCH (remarcação)': [
                ('patch', f'/api/v1/appointments/{b.agendamento.pk}/', {'data_hora': self.livre.isoformat()}),
                ('patch', '/api/v1/appointments/999999/', {'data_hora': self.livre.isoformat()}),
            ],
            'PUT': [
                ('put', f'/api/v1/appointments/{b.agendamento.pk}/', self.corpo(b, self.livre)),
                ('put', '/api/v1/appointments/999999/', self.corpo(b, self.livre)),
            ],
            'DELETE (cancelamento)': [
                ('delete', f'/api/v1/appointments/{b.agendamento.pk}/', None),
                ('delete', '/api/v1/appointments/999999/', None),
            ],
            'horários livres': [
                ('get', '/api/v1/appointments/available-slots/', {'barbeiro': b.barbeiro.pk, 'servico': b.servico.pk, 'data': dia_ocupado.isoformat()}),
                ('get', '/api/v1/appointments/available-slots/', {'barbeiro': b.barbeiro.pk, 'servico': b.servico.pk, 'data': dia_livre.isoformat()}),
                ('get', '/api/v1/appointments/available-slots/', {'barbeiro': 999999, 'servico': 999999, 'data': dia_ocupado.isoformat()}),
            ],
            'listagem filtrada pelo barbeiro': [
                ('get', '/api/v1/appointments/', {'barbeiro': b.barbeiro.pk}),
                ('get', '/api/v1/appointments/', {'barbeiro': 999999}),
            ],
        }
        for grupo, pedidos in grupos.items():
            with self.subTest(operacao=grupo):
                vistas = set()
                for metodo, url, dados in pedidos:
                    with CaptureQueriesContext(connection) as consultas:
                        if metodo in ('get', 'delete'):
                            resposta = getattr(api, metodo)(url, dados)
                        else:
                            resposta = getattr(api, metodo)(url, dados, format='json')
                    vistas.add((resposta.status_code, resposta.content))
                    self.assertGreaterEqual(resposta.status_code, 400)
                    self.assert_sem_leitura_de_tenant(consultas.captured_queries, self.sem)
                self.assertEqual(len(vistas), 1, vistas)
        self.assertEqual(self.fotografia(), antes)


class OutraBarbeariaTests(CenarioTen02):
    """Caso 5: quem tem barbearia também não sonda a agenda de outra."""

    def test_usuario_de_a_nao_sonda_a_agenda_de_b(self):
        b = self.b
        for papel, usuario in (('cliente', self.a.cliente), ('barbeiro', self.a.barbeiro.user), ('admin', self.a.admin)):
            api = self.entrar(usuario)
            proprio = {'cliente': self.a.cliente.pk, 'barbeiro': self.a.barbeiro.pk, 'servico': self.a.servico.pk}
            casos = {
                'ocupado': {**proprio, 'barbeiro': b.barbeiro.pk, 'data_hora': self.ocupado.isoformat()},
                'livre': {**proprio, 'barbeiro': b.barbeiro.pk, 'data_hora': self.livre.isoformat()},
                'inexistente': {**proprio, 'barbeiro': 999999, 'data_hora': self.ocupado.isoformat()},
            }
            corpos = set()
            for nome, corpo in casos.items():
                with self.subTest(papel=papel, caso=nome):
                    with CaptureQueriesContext(connection) as consultas:
                        resposta = api.post('/api/v1/appointments/', corpo, format='json')
                    self.assertEqual(resposta.status_code, 400)
                    corpos.add(re.sub(r'\d+', '<n>', resposta.content.decode()))
                    agenda = [c['sql'] for c in consultas.captured_queries if 'appointments_appointment' in tabelas(c)]
                    self.assertEqual(agenda, [], 'a agenda foi consultada para um barbeiro de outra barbearia')
            self.assertEqual(len(corpos), 1, corpos)
        self.assertEqual(Appointment.objects.filter(barbeiro=b.barbeiro).count(), 1)


class FluxosLegitimosTen02Tests(CenarioTen02):
    """Casos 6 e 7: o fluxo normal e o de uma conta nova continuam funcionando."""

    def test_usuario_legitimo_agenda_na_propria_barbearia(self):
        a = self.a
        api = self.entrar(a.cliente)
        resposta = api.post('/api/v1/appointments/', self.corpo(a, self.livre), format='json')
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(resposta.json()['barbershop'], a.shop.pk)
        # Dentro da própria barbearia, a disponibilidade continua sendo validada.
        with CaptureQueriesContext(connection) as consultas:
            ocupado = api.post('/api/v1/appointments/', self.corpo(a, self.ocupado), format='json')
        self.assertEqual(ocupado.status_code, 400)
        self.assertEqual(ocupado.json(), {'data_hora': ['Este barbeiro já possui um agendamento neste horário.']})
        agenda = [c['sql'] for c in consultas.captured_queries if 'appointments_appointment' in tabelas(c) and '"barbeiro_id" =' in c['sql']]
        self.assertTrue(agenda)
        for sql in agenda:
            self.assertRegex(sql, rf'"barbeiro_id" = {a.barbeiro.pk}\b')
        for usuario, extra in ((a.admin, {'data_hora': (self.livre + timedelta(hours=1)).isoformat()}),
                               (a.barbeiro.user, {'data_hora': (self.livre + timedelta(hours=2)).isoformat()})):
            with self.subTest(papel=usuario.tipo_perfil):
                resposta = self.entrar(usuario).post('/api/v1/appointments/', self.corpo(a, self.livre, **extra), format='json')
                self.assertEqual(resposta.status_code, 201, resposta.content)

    def test_cadastro_publico_e_onboarding(self):
        cache.clear()
        cadastro = APIClient().post('/api/v1/auth/register/', {'email': 'nova@gama.test', 'nome': 'Dona Gama', 'password': SENHA}, format='json')
        self.assertEqual(cadastro.status_code, 201, cadastro.content)
        dona = User.objects.get(email='nova@gama.test')
        api = self.entrar(dona)
        self.assertEqual(api.get('/api/v1/users/me/').status_code, 200)
        self.assertEqual(api.post('/api/v1/appointments/', self.corpo(self.b, self.livre), format='json').json(), RECUSA)
        self.assertEqual(api.get('/api/v1/appointments/').json()['count'], 0)

        loja = api.post('/api/v1/barbershops/', {
            'nome': 'Barbearia Gama', 'endereco': 'Rua Gama', 'telefone': '11977777777', 'email': 'contato@gama.test',
            'horario_abertura': '08:00', 'horario_fechamento': '18:00',
        }, format='json')
        self.assertEqual(loja.status_code, 201, loja.content)
        servico = api.post('/api/v1/services/', {'nome': 'Corte Gama', 'preco': '30.00', 'duracao': 30}, format='json')
        self.assertEqual(servico.status_code, 201, servico.content)
        ids = []
        for email in ('c1@gama.test', 'c2@gama.test'):
            criado = api.post('/api/v1/users/', {'email': email, 'nome': email, 'password': SENHA, 'tipo_perfil': 'cliente'}, format='json')
            self.assertEqual(criado.status_code, 201, criado.content)
            ids.append(criado.json()['id'])
        barbeiro = api.post('/api/v1/barbers/', {'user': ids[0]}, format='json')
        self.assertEqual(barbeiro.status_code, 201, barbeiro.content)
        # O mesmo token, emitido antes do onboarding, passa a agendar: a barbearia vem do banco, não do token.
        agendamento = api.post('/api/v1/appointments/', {
            'cliente': ids[1], 'barbeiro': barbeiro.json()['id'], 'servico': servico.json()['id'], 'data_hora': self.livre.isoformat(),
        }, format='json')
        self.assertEqual(agendamento.status_code, 201, agendamento.content)
        self.assertEqual(agendamento.json()['barbershop'], loja.json()['id'])

    def test_superusuario(self):
        api = self.entrar(self.superusuario)
        total = Appointment.objects.count()
        resposta = api.post('/api/v1/appointments/', self.corpo(self.a, self.livre), format='json')
        self.assertEqual((resposta.status_code, resposta.json()), (403, RECUSA))
        self.assertEqual(Appointment.objects.count(), total)
        # Editar continua permitido ao operador da plataforma, dentro da barbearia do registro.
        resposta = api.patch(f'/api/v1/appointments/{self.a.agendamento.pk}/', {'status': 'confirmado'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual(api.get('/api/v1/appointments/', {'barbeiro': self.b.barbeiro.pk}).json()['count'], 1)
