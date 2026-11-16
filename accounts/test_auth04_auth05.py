"""
AUTH-04 e AUTH-05: regra única do e-mail de login (accounts.emails) e garantia pelo banco (accounts.0006).

Regra: str.strip() → só ASCII imprimível U+0021..U+007E (checado antes de converter) → minúsculas. A sintaxe continua
com o validador do projeto (o EmailField do DRF na API; o EmailField do model no Django Admin).

Os testes de concorrência real e de equivalência Python × PostgreSQL rodam só no PostgreSQL (no SQLite, são pulados);
a equivalência exige a ordenação pt_BR do banco real. Dados fictícios (domínios .test).
"""
import base64
import importlib
import re
import threading
from datetime import timedelta
from io import StringIO
from unittest import mock, skipUnless

from django.contrib.auth import authenticate
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.validators import UniqueValidator

from accounts.emails import (
    RESTRICAO_CHECK,
    RESTRICAO_UNIQUE_DO_CAMPO,
    RESTRICAO_UNIQUE_LOWER,
    e_violacao_da_unicidade_do_email,
    forma_canonica,
    normalizar_email,
)
from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from accounts.models import User
from accounts.serializers import EmailNormalizadoField
from accounts.throttles import tenta_trocar_email
from barbershops.models import Barber, Barbershop
from services.models import Service

SENHA = 'Navalha-Fict-2026!'
UNICIDADE = 'usuário com este e-mail já existe.'
INVALIDO = 'Insira um endereço de email válido.'
NAO_STRINGS = [123, 1.5, True, [], {}, ['a@b.test'], {'email': 'a@b.test'}]
ESPACOS_PYTHON = [chr(c) for c in range(0x110000) if chr(c).isspace()]
# Os 56 caracteres em que str.lower() (Python 3.12) e lower() (PostgreSQL, pt_BR.UTF-8) divergem (seção 30), mais o
# sinal de Kelvin e o de Angstrom, que viram letras ASCII ou latinas ao converter.
DIVERGENTES = ['İ', 'Ᲊ', 'Ɤ', 'Ꟍ', '꟎', '꟒', '꟔', 'Ꟛ', 'Ƛ', '\U00010d50']
CONVERTEM_PARA_ASCII = ['K', 'Å']
INVISIVEIS = ['​', '﻿', '­', '‌', '‍', '⁠', '͏', '᠋', '︀', '️']
MIGRACAO = importlib.import_module('accounts.migrations.0006_email_normalizado')


def em_postgresql():
    return connection.vendor == 'postgresql'


class SemLimites:
    """Os limites reais de login, cadastro e recuperação (5/min, 10/h…) não são o assunto aqui (exceto em LimitesTests)."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        p = mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {k: '100000/minute' for k in SimpleRateThrottle.THROTTLE_RATES})
        p.start()
        self.addCleanup(p.stop)


class Cenario(SemLimites, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = Barbershop.objects.create(nome='Alfa', endereco='Rua 1', telefone='11900000001', email='contato@alfa.test',
                                          horario_abertura='08:00', horario_fechamento='18:00')
        cls.b = Barbershop.objects.create(nome='Beta', endereco='Rua 2', telefone='11900000002', email='contato@beta.test',
                                          horario_abertura='08:00', horario_fechamento='18:00')
        cls.admin_a = User.objects.create_user(email='admin.a@alfa.test', nome='Ana', password=SENHA, tipo_perfil='admin', barbershop=cls.a)
        cls.admin_b = User.objects.create_user(email='admin.b@beta.test', nome='Beatriz', password=SENHA, tipo_perfil='admin', barbershop=cls.b)
        cls.cliente_a = User.objects.create_user(email='cliente.a@alfa.test', nome='Carlos', password=SENHA, barbershop=cls.a)
        cls.cliente_a2 = User.objects.create_user(email='cliente.a2@alfa.test', nome='Celia', password=SENHA, barbershop=cls.a)
        cls.cliente_b = User.objects.create_user(email='cliente.b@beta.test', nome='Clara', password=SENHA, barbershop=cls.b)
        cls.inicio = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)

    def como(self, usuario):
        c = APIClient()
        c.force_authenticate(usuario)
        return c

    def cadastrar(self, email, senha=SENHA):
        return APIClient().post('/api/v1/auth/register/', {'nome': 'Pessoa Fictícia', 'email': email, 'password': senha}, format='json')

    def entrar(self, email, senha=SENHA):
        return APIClient().post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')

    def cliente_com_token(self, email, senha=SENHA):
        login = self.entrar(email, senha)
        self.assertEqual(login.status_code, 200, login.content)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {login.json()["access"]}')
        return c

    def mensagem_de_recuperacao(self):
        m = mail.outbox[-1]
        uid = re.search(r'^uid: (\S+)$', m.body, re.M).group(1)
        return m.to, int(base64.urlsafe_b64decode(uid + '=' * (-len(uid) % 4)).decode())


# ------------------------------------------------------------------------------------------------------------- regra
class RegraUnicaTests(TestCase):
    def test_ascii_valido_minusculas_e_espacos_externos(self):
        self.assertEqual(forma_canonica('cliente.b@beta.test'), 'cliente.b@beta.test')
        self.assertEqual(forma_canonica('Cliente.B@BETA.TEST'), 'cliente.b@beta.test')
        self.assertEqual(forma_canonica("a!#$%&'*+/=?^_`{|}~-b@exemplo.test"), "a!#$%&'*+/=?^_`{|}~-b@exemplo.test")
        self.assertEqual(len(ESPACOS_PYTHON), 29)
        for espaco in ESPACOS_PYTHON:
            with self.subTest(espaco=f'U+{ord(espaco):04X}'):
                self.assertEqual(forma_canonica(f'{espaco}Cliente.B@Beta.Test{espaco}{espaco}'), 'cliente.b@beta.test')

    def test_espacos_internos_sao_recusados(self):
        for espaco in ESPACOS_PYTHON:
            with self.subTest(espaco=f'U+{ord(espaco):04X}'):
                self.assertIsNone(forma_canonica(f'cliente{espaco}b@beta.test'))
                self.assertIsNone(forma_canonica(f'cliente.b@beta{espaco}.test'))

    def test_acentos_unicode_e_punycode(self):
        for valor in ['joão@exemplo.test', 'cliente@álfa.test', 'cliente@ÁLFA.test', 'x@straße.test']:
            with self.subTest(valor=valor):
                self.assertIsNone(forma_canonica(valor))
        self.assertEqual(forma_canonica('Cliente@XN--LFA-1LA.test'), 'cliente@xn--lfa-1la.test')

    def test_divergentes_e_os_que_viram_ascii_sao_recusados_antes_de_converter(self):
        for c in DIVERGENTES + CONVERTEM_PARA_ASCII + INVISIVEIS:
            with self.subTest(cp=f'U+{ord(c):04X}'):
                for valor in (f'x@a{c}b.test', f'x@exemplo.test{c}', f'{c}x@exemplo.test', f'x{c}y@exemplo.test'):
                    self.assertIsNone(forma_canonica(valor))
        self.assertEqual('K'.lower(), 'k')  # o motivo de checar a faixa antes: o Kelvin viraria "k"
        self.assertIsNone(forma_canonica('Kelvin@exemplo.test'))

    def test_nenhum_ponto_de_codigo_fora_do_ascii_passa(self):
        aceitos = [c for c in range(0x80, 0x110000) if not 0xD800 <= c <= 0xDFFF and forma_canonica(f'a{chr(c)}b@x.test') is not None]
        self.assertEqual(aceitos, [])
        controles = [c for c in list(range(0x01, 0x21)) + [0x7F] if forma_canonica(f'a{chr(c)}b@x.test') is not None]
        self.assertEqual(controles, [])

    def test_entradas_que_nao_sao_texto(self):
        for valor in NAO_STRINGS + [None, b'a@b.test']:
            with self.subTest(valor=repr(valor)):
                self.assertIsNone(forma_canonica(valor))
                with self.assertRaises(ValidationError):
                    normalizar_email(valor)
        with self.assertRaises(ValidationError):
            normalizar_email('')

    def test_campo_da_api_responde_como_antes_para_entradas_invalidas(self):
        """Mesmo código e mensagem do EmailField do DRF que já era usado (null, blank, invalid)."""
        novo, antigo = EmailNormalizadoField(max_length=254), serializers.EmailField(max_length=254)
        for campo in (novo, antigo):
            campo.bind('email', serializers.Serializer())
        for valor in NAO_STRINGS + [None, '', '   ', b'a@b.test', 'nao-e-email']:
            with self.subTest(valor=repr(valor)):
                erros = []
                for campo in (novo, antigo):
                    with self.assertRaises(serializers.ValidationError) as ctx:
                        campo.run_validation(valor)
                    erros.append([(str(d), d.code) for d in ctx.exception.detail])
                self.assertEqual(erros[0], erros[1])
        for valor in ['x@álfa.test', 'x@exem​plo.test', 'a b@x.test']:
            with self.subTest(valor=valor), self.assertRaises(serializers.ValidationError) as ctx:
                novo.run_validation(valor)
            self.assertEqual([(str(d), d.code) for d in ctx.exception.detail], [(INVALIDO, 'invalid')])
        self.assertEqual(novo.run_validation('  Cliente.B@BETA.test '), 'cliente.b@beta.test')

    def test_reconhece_so_a_violacao_da_unicidade_do_email(self):
        class ErroDoDriver(Exception):
            pass

        def erro_pg(nome):
            causa = ErroDoDriver('x')
            causa.diag = mock.Mock(constraint_name=nome)
            erro = IntegrityError('x')
            erro.__cause__ = causa
            return erro
        self.assertTrue(e_violacao_da_unicidade_do_email(erro_pg(RESTRICAO_UNIQUE_DO_CAMPO)))
        self.assertTrue(e_violacao_da_unicidade_do_email(erro_pg(RESTRICAO_UNIQUE_LOWER)))
        self.assertFalse(e_violacao_da_unicidade_do_email(erro_pg(RESTRICAO_CHECK)))
        self.assertFalse(e_violacao_da_unicidade_do_email(erro_pg('barbershops_barber_user_id_key')))
        self.assertTrue(e_violacao_da_unicidade_do_email(IntegrityError('UNIQUE constraint failed: accounts_user.email')))
        self.assertTrue(e_violacao_da_unicidade_do_email(IntegrityError(f"UNIQUE constraint failed: index '{RESTRICAO_UNIQUE_LOWER}'")))
        self.assertFalse(e_violacao_da_unicidade_do_email(IntegrityError('CHECK constraint failed: accounts_user_email_normalizado')))
        self.assertFalse(e_violacao_da_unicidade_do_email(IntegrityError('NOT NULL constraint failed: accounts_user.nome')))


# --------------------------------------------------------------------------------------------- cadastro público
class CadastroPublicoTests(Cenario):
    def test_formas_aceitas_e_gravadas_na_forma_canonica(self):
        for digitado, gravado in [('nova.um@exemplo.test', 'nova.um@exemplo.test'), ('Nova.Dois@EXEMPLO.TEST', 'nova.dois@exemplo.test'),
                                  ('  nova.tres@exemplo.test 　', 'nova.tres@exemplo.test'),
                                  ('nova.quatro@XN--LFA-1LA.test', 'nova.quatro@xn--lfa-1la.test')]:
            with self.subTest(digitado=digitado):
                r = self.cadastrar(digitado)
                self.assertEqual(r.status_code, 201, r.content)
                self.assertEqual(r.json()['email'], gravado)
                self.assertEqual(User.objects.get(pk=r.json()['id']).email, gravado)

    def test_formas_recusadas_com_a_resposta_de_email_invalido(self):
        referencia = self.cadastrar('nao-e-email')
        self.assertEqual(referencia.status_code, 400)
        total = User.objects.count()
        for valor in ['joão@exemplo.test', 'nova@álfa.test', 'nova@ÁLFA.TEST', 'no va@exemplo.test', 'nova@exem​plo.test',
                      'nova@exemplo.test﻿', 'nova@exem­plo.test', 'nova@İ.test', 'nova@aꟋb.test', 'Knova@x.test']:
            with self.subTest(valor=valor):
                r = self.cadastrar(valor)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json(), {'email': [INVALIDO]})
                self.assertEqual(r.json(), referencia.json())
        for valor in NAO_STRINGS:
            with self.subTest(valor=repr(valor)):
                r = self.cadastrar(valor)
                self.assertEqual((r.status_code, r.json()), (400, {'email': [INVALIDO]}))
        self.assertEqual(User.objects.count(), total)

    def test_variacao_de_caixa_de_conta_existente_e_recusada(self):
        total = User.objects.count()
        for valor in ['Cliente.B@beta.test', 'cliente.b@BETA.TEST', 'CLIENTE.B@BETA.TEST', '  cliente.b@beta.test  ', 'ADMIN.A@alfa.test']:
            with self.subTest(valor=valor):
                r = self.cadastrar(valor)
                self.assertEqual((r.status_code, r.json()), (400, {'email': [UNICIDADE]}))
        self.assertEqual(User.objects.count(), total)

    def test_dono_cadastra_entra_cria_a_barbearia_e_agenda(self):
        """Fluxo atual do cadastro público (dono): conta sem barbearia → login → onboarding → agenda pela própria barbearia."""
        r = self.cadastrar('Dono.Gama@GAMA.test')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIsNone(r.json()['barbershop'])
        dono = self.cliente_com_token('Dono.Gama@GAMA.test')  # a tela entra logo depois com o mesmo texto digitado
        self.assertEqual(dono.get('/api/v1/users/me/').json()['email'], 'dono.gama@gama.test')
        loja = dono.post('/api/v1/barbershops/', {'nome': 'Gama', 'endereco': 'Rua 3', 'telefone': '11977777777', 'email': 'contato@gama.test',
                                                  'horario_abertura': '08:00', 'horario_fechamento': '18:00'}, format='json')
        self.assertEqual(loja.status_code, 201, loja.content)
        self.assertEqual(User.objects.get(email='dono.gama@gama.test').tipo_perfil, 'admin')
        servico = dono.post('/api/v1/services/', {'nome': 'Corte', 'preco': '30.00', 'duracao': 30}, format='json')
        barbeiro = dono.post('/api/v1/users/', {'email': 'Barbeiro@Gama.Test', 'nome': 'Bruno', 'password': SENHA, 'tipo_perfil': 'barbeiro',
                                                'especialidade': 'Corte'}, format='json')
        cliente = dono.post('/api/v1/users/', {'email': ' Cliente@GAMA.test ', 'nome': 'Caio', 'password': SENHA, 'tipo_perfil': 'cliente'}, format='json')
        for resposta in (servico, barbeiro, cliente):
            self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual((barbeiro.json()['email'], cliente.json()['email']), ('barbeiro@gama.test', 'cliente@gama.test'))
        perfil = Barber.objects.get(user__email='barbeiro@gama.test')
        ag = dono.post('/api/v1/appointments/', {'cliente': cliente.json()['id'], 'barbeiro': perfil.pk, 'servico': servico.json()['id'],
                                                 'data_hora': (self.inicio + timedelta(hours=1)).isoformat()}, format='json')
        self.assertEqual(ag.status_code, 201, ag.content)

    def test_cliente_cadastrado_pelo_admin_entra_com_outra_caixa_e_agenda(self):
        servico = Service.objects.create(barbershop=self.a, nome='Corte', preco='40.00', duracao=30)
        barbeiro = Barber.objects.create(user=User.objects.create_user(email='barbeiro.a@alfa.test', nome='Beto', password=SENHA,
                                                                       tipo_perfil='barbeiro', barbershop=self.a), barbershop=self.a)
        cliente = self.cliente_com_token(' CLIENTE.A@Alfa.Test ')
        # O mesmo corpo da tela de agendamento (AppointmentCreatePage): `cliente` é o próprio id.
        ag = cliente.post('/api/v1/appointments/', {'cliente': self.cliente_a.pk, 'barbeiro': barbeiro.pk, 'servico': servico.pk,
                                                    'data_hora': (self.inicio + timedelta(hours=2)).isoformat()}, format='json')
        self.assertEqual(ag.status_code, 201, ag.content)
        self.assertEqual(ag.json()['cliente'], self.cliente_a.pk)

    def test_conta_sem_barbearia_continua_recusada_no_agendamento(self):
        self.assertEqual(self.cadastrar('sem.barbearia@exemplo.test').status_code, 201)
        conta = self.cliente_com_token('SEM.BARBEARIA@exemplo.test')
        r = conta.post('/api/v1/appointments/', {'barbeiro': 1, 'servico': 1, 'data_hora': self.inicio.isoformat()}, format='json')
        self.assertEqual((r.status_code, r.json()), (403, {'detail': 'Usuário sem barbearia vinculada.'}))


# ------------------------------------------------------------------------------------------ criação e edição
class CriacaoEEdicaoTests(Cenario):
    def criar(self, admin, email, **extra):
        return self.como(admin).post('/api/v1/users/', {'email': email, 'nome': 'Novo', 'password': SENHA, 'tipo_perfil': 'cliente', **extra},
                                     format='json')

    def test_criacao_pelo_admin(self):
        r = self.criar(self.admin_a, '  Novo.Cliente@ALFA.test ')
        self.assertEqual((r.status_code, r.json()['email']), (201, 'novo.cliente@alfa.test'))
        r = self.criar(self.admin_a, 'Novo.Barbeiro@Alfa.Test', tipo_perfil='barbeiro', especialidade='Barba')
        self.assertEqual((r.status_code, r.json()['email']), (201, 'novo.barbeiro@alfa.test'))
        self.assertEqual(self.criar(self.admin_a, 'novo@álfa.test').json(), {'email': [INVALIDO]})

    def test_duplicidade_na_mesma_barbearia_e_em_outra(self):
        antes_b = User.objects.filter(barbershop=self.b).values_list('id', 'email', 'nome').order_by('id')
        antes_b = list(antes_b)
        total = User.objects.count()
        for email in ['CLIENTE.A2@alfa.test', 'cliente.a2@ALFA.TEST', 'Cliente.B@Beta.Test', ' CLIENTE.B@BETA.TEST ', 'Admin.B@beta.test']:
            with self.subTest(email=email):
                r = self.criar(self.admin_a, email)
                self.assertEqual((r.status_code, r.json()), (400, {'email': [UNICIDADE]}))
        self.assertEqual(User.objects.count(), total)
        self.assertEqual(list(User.objects.filter(barbershop=self.b).values_list('id', 'email', 'nome').order_by('id')), antes_b)

    def test_edicao_do_proprio_email(self):
        c = self.como(self.cliente_a)
        url = f'/api/v1/users/{self.cliente_a.pk}/'
        r = c.patch(url, {'email': ' Carlos.Novo@ALFA.TEST '}, format='json')
        self.assertEqual((r.status_code, r.json()['email']), (200, 'carlos.novo@alfa.test'))
        r = c.patch(url, {'nome': 'Carlos', 'email': 'CARLOS.NOVO@alfa.test'}, format='json')  # o próprio, em outra caixa
        self.assertEqual((r.status_code, r.json()['email']), (200, 'carlos.novo@alfa.test'))
        for email in ['Cliente.A2@alfa.test', 'CLIENTE.B@BETA.TEST']:
            with self.subTest(email=email):
                self.assertEqual(c.patch(url, {'email': email}, format='json').json(), {'email': [UNICIDADE]})
        self.assertEqual(c.patch(url, {'email': 'carlos@álfa.test'}, format='json').json(), {'email': [INVALIDO]})
        r = c.put(url, {'email': 'Carlos.Put@Alfa.Test', 'nome': 'Carlos'}, format='json')
        self.assertEqual((r.status_code, r.json()['email']), (200, 'carlos.put@alfa.test'))
        self.cliente_a.refresh_from_db()
        self.assertEqual(self.cliente_a.email, 'carlos.put@alfa.test')

    def test_admin_edita_o_email_de_um_cliente(self):
        url = f'/api/v1/users/{self.cliente_a2.pk}/'
        r = self.como(self.admin_a).patch(url, {'email': 'CELIA@ALFA.TEST'}, format='json')
        self.assertEqual((r.status_code, r.json()['email']), (200, 'celia@alfa.test'))
        r = self.como(self.admin_a).patch(url, {'email': 'cliente.b@BETA.test'}, format='json')
        self.assertEqual((r.status_code, r.json()), (400, {'email': [UNICIDADE]}))


# -------------------------------------------------------------------------------------- login e recuperação
class LoginERecuperacaoTests(Cenario):
    def test_login_sem_diferenciar_caixa_e_com_espacos(self):
        for digitado in ['cliente.b@beta.test', 'Cliente.B@beta.test', 'cliente.b@BETA.TEST', 'CLIENTE.B@BETA.TEST', '  cliente.b@beta.test  ']:
            with self.subTest(digitado=digitado):
                me = self.cliente_com_token(digitado).get('/api/v1/users/me/').json()
                self.assertEqual((me['id'], me['barbershop']), (self.cliente_b.pk, self.b.pk))

    def test_login_errado_tem_a_mesma_resposta_para_existente_inexistente_e_fora_da_regra(self):
        respostas = [self.entrar(e, 'Senha-Errada-123!') for e in ['CLIENTE.B@BETA.TEST', 'ninguem@exemplo.test', 'cliente.b@bétá.test', '']]
        self.assertEqual({r.status_code for r in respostas[:3]}, {401})
        self.assertEqual(len({r.content for r in respostas[:3]}), 1)
        self.assertEqual(respostas[3].status_code, 400)  # vazio: validação do campo, como antes
        self.assertIsNone(authenticate(email=['nao', 'texto'], password=SENHA))

    def test_login_do_django_admin_e_createsuperuser_usam_a_mesma_regra(self):
        staff = User.objects.create_superuser(email='Operador@Plataforma.Test', nome='Op', password=SENHA)
        self.assertEqual(staff.email, 'operador@plataforma.test')
        self.assertTrue(self.client.login(email='OPERADOR@plataforma.test', password=SENHA))
        with self.assertRaises(CommandError):
            call_command('createsuperuser', interactive=False, email='OPERADOR@PLATAFORMA.TEST', nome='Outro', stdout=StringIO(), stderr=StringIO())

    def test_recuperacao_vai_para_a_conta_canonica(self):
        for digitado in ['cliente.b@beta.test', 'CLIENTE.B@BETA.TEST', '  Cliente.B@Beta.Test  ']:
            with self.subTest(digitado=digitado):
                mail.outbox = []
                r = APIClient().post('/api/v1/auth/password/reset/', {'email': digitado}, format='json')
                self.assertEqual((r.status_code, r.content), (204, b''))
                para, conta = self.mensagem_de_recuperacao()
                self.assertEqual((para, conta), (['cliente.b@beta.test'], self.cliente_b.pk))
                self.assertEqual(User.objects.get(pk=conta).email, para[0])

    def test_recuperacao_inexistente_e_inativa_respondem_igual(self):
        inativa = User.objects.create_user(email='inativa@beta.test', nome='Ivo', password=SENHA, barbershop=self.b, is_active=False)
        respostas = []
        for email in ['ninguem@exemplo.test', inativa.email.upper(), 'cliente.b@beta.test']:
            mail.outbox = []
            r = APIClient().post('/api/v1/auth/password/reset/', {'email': email}, format='json')
            respostas.append((r.status_code, r.content))
            para, conta = self.mensagem_de_recuperacao()
            if email != 'cliente.b@beta.test':
                self.assertEqual(conta, 0)  # o envio fictício de sempre, nunca para uma conta
        self.assertEqual(len(set(respostas)), 1)
        r = APIClient().post('/api/v1/auth/password/reset/', {'email': 'cliente.b@bétá.test'}, format='json')
        self.assertEqual((r.status_code, r.json()), (400, {'email': [INVALIDO]}))

    def test_auth04_variacao_de_caixa_nao_pode_existir_nem_desviar_a_recuperacao(self):
        self.assertEqual(self.cadastrar('Cliente.B@beta.test').json(), {'email': [UNICIDADE]})  # pela API
        with self.assertRaises(IntegrityError), transaction.atomic():  # pelo manager: normaliza e o banco recusa
            User.objects.create_user(email='CLIENTE.B@BETA.TEST', nome='Aaron Variante', password=SENHA)
        outra = User.objects.create_user(email='aaron@exemplo.test', nome='Aaron Variante', password=SENHA)
        with self.assertRaises(IntegrityError), transaction.atomic():  # contornando o save(): o banco recusa
            User.objects.filter(pk=outra.pk).update(email='Cliente.B@beta.test')
        mail.outbox = []
        APIClient().post('/api/v1/auth/password/reset/', {'email': 'cliente.b@beta.test'}, format='json')
        self.assertEqual(self.mensagem_de_recuperacao(), (['cliente.b@beta.test'], self.cliente_b.pk))
        self.assertEqual(User.objects.filter(email__iexact='cliente.b@beta.test').count(), 1)


# -------------------------------------------------------------------------- Django Admin, model e caminhos diretos
class AdminModelECaminhosDiretosTests(Cenario):
    def formulario(self, email):
        return CustomUserCreationForm(data={'email': email, 'nome': 'Admin Form', 'tipo_perfil': 'cliente', 'barbershop': self.a.pk,
                                            'password1': SENHA, 'password2': SENHA})

    def test_formularios_do_django_admin(self):
        f = self.formulario('  Formulario@ALFA.Test ')
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.save().email, 'formulario@alfa.test')
        for email, mensagem in [('CLIENTE.B@beta.test', 'Usuário com este E-mail já existe.'),
                                ('cliente.b@BETA.TEST', 'Usuário com este E-mail já existe.'),
                                ('x@álfa.test', INVALIDO), ('x@ｂｅｔａ.test', INVALIDO), ('x@exem​plo.test', INVALIDO)]:
            with self.subTest(email=email):
                f = self.formulario(email)
                self.assertFalse(f.is_valid())
                # Um erro só, no campo, sem o nome interno de restrição nenhuma.
                self.assertEqual(dict(f.errors), {'email': [mensagem]})
        dados = {**CustomUserChangeForm(instance=self.cliente_a2).initial, 'email': 'CLIENTE.B@BETA.TEST', 'password': self.cliente_a2.password}
        dados = {k: ('' if v is None else v) for k, v in dados.items()}
        f = CustomUserChangeForm(data=dados, instance=self.cliente_a2)
        self.assertFalse(f.is_valid())
        self.assertIn('email', f.errors)

    def test_manager_e_save_gravam_a_forma_canonica(self):
        u = User.objects.create_user(email=' Manager@ALFA.Test ', nome='M', password=SENHA)
        self.assertEqual(u.email, 'manager@alfa.test')
        u.email = 'SAVE@Alfa.Test'
        u.save()
        u.refresh_from_db()
        self.assertEqual(u.email, 'save@alfa.test')
        for valor in ['save@álfa.test', 'sa ve@alfa.test', '', None, 123]:
            with self.subTest(valor=repr(valor)):
                u.email = valor
                with self.assertRaises(ValidationError):
                    u.save()
        u.refresh_from_db()
        u.nome = 'Outro'
        u.save(update_fields=['nome'])  # sem gravar o e-mail, ele não é tocado
        self.assertEqual(User.objects.get(pk=u.pk).email, 'save@alfa.test')
        for valor in [None, 123, ['a@b.test'], 'x@álfa.test']:
            with self.subTest(natural=repr(valor)), self.assertRaises(User.DoesNotExist):
                User.objects.get_by_natural_key(valor)
        self.assertEqual(User.objects.get_by_natural_key(' SAVE@ALFA.TEST ').pk, u.pk)

    def test_update_e_bulk_create_contornam_o_save_e_o_banco_recusa(self):
        casos = [
            ('update maiúsculas', lambda: User.objects.filter(pk=self.cliente_a.pk).update(email='Cliente.A@alfa.test')),
            ('update com espaço', lambda: User.objects.filter(pk=self.cliente_a.pk).update(email='cliente.a@alfa.test ')),
            ('update não ASCII', lambda: User.objects.filter(pk=self.cliente_a.pk).update(email='cliente.a@álfa.test')),
            ('update para outra conta', lambda: User.objects.filter(pk=self.cliente_a.pk).update(email='cliente.b@beta.test')),
            ('bulk_create maiúsculas', lambda: User.objects.bulk_create([User(email='BULK@alfa.test', nome='B', password='!')])),
            ('bulk_create variação', lambda: User.objects.bulk_create([User(email='CLIENTE.B@BETA.TEST', nome='B', password='!')])),
        ]
        for nome, operacao in casos:
            with self.subTest(caso=nome), self.assertRaises(IntegrityError), transaction.atomic():
                operacao()
        self.cliente_a.refresh_from_db()
        self.assertEqual(self.cliente_a.email, 'cliente.a@alfa.test')
        self.assertEqual(User.objects.count(), 5)


# ---------------------------------------------------------------------------------------- IntegrityError → 400
class IntegrityErrorTests(Cenario):
    def sem_validador_de_unicidade(self):
        return mock.patch.object(UniqueValidator, '__call__', lambda self, value, serializer_field: None)

    def test_pedido_simultaneo_simulado_responde_400_e_a_transacao_continua_integra(self):
        total = User.objects.count()
        with self.sem_validador_de_unicidade():
            respostas = [
                self.cadastrar('CLIENTE.B@BETA.TEST'),
                self.como(self.admin_a).post('/api/v1/users/', {'email': 'Cliente.B@beta.test', 'nome': 'X', 'password': SENHA,
                                                                'tipo_perfil': 'cliente'}, format='json'),
                self.como(self.cliente_a).patch(f'/api/v1/users/{self.cliente_a.pk}/', {'email': 'cliente.b@BETA.test'}, format='json'),
            ]
        for r in respostas:
            self.assertEqual((r.status_code, r.json()), (400, {'email': [UNICIDADE]}))
        self.assertEqual(User.objects.count(), total)  # a transação externa segue utilizável
        self.cliente_a.refresh_from_db()
        self.assertEqual(self.cliente_a.email, 'cliente.a@alfa.test')

    def test_outro_integrity_error_nao_vira_email_duplicado(self):
        api = APIClient()
        api.raise_request_exception = False
        with mock.patch.object(User.objects, 'create_user', side_effect=IntegrityError('NOT NULL constraint failed: accounts_user.nome')):
            r = api.post('/api/v1/auth/register/', {'nome': 'X', 'email': 'outro.erro@exemplo.test', 'password': SENHA}, format='json')
        self.assertEqual(r.status_code, 500)
        self.assertNotIn(UNICIDADE.encode(), r.content)

    def test_respostas_iguais_com_debug_true_e_false(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                invalido = self.cadastrar('nova@álfa.test')
                duplicado = self.cadastrar('CLIENTE.B@BETA.TEST')
                with self.sem_validador_de_unicidade():
                    corrida = self.cadastrar('Cliente.B@beta.test')
                self.assertEqual((invalido.status_code, invalido.json()), (400, {'email': [INVALIDO]}))
                for r in (duplicado, corrida):
                    self.assertEqual((r.status_code, r.json()), (400, {'email': [UNICIDADE]}))
                    self.assertEqual(r['Content-Type'], 'application/json')


# ---------------------------------------------------------------------------- isolamento e limites existentes
class IsolamentoTests(Cenario):
    def test_email_de_outra_barbearia_em_qualquer_caixa_nao_entra_em_a(self):
        for email in ['CLIENTE.B@BETA.TEST', 'Admin.B@Beta.Test']:
            with self.subTest(email=email):
                r = self.como(self.admin_a).post('/api/v1/users/', {'email': email, 'nome': 'X', 'password': SENHA, 'tipo_perfil': 'cliente'},
                                                 format='json')
                self.assertEqual(r.status_code, 400)
        self.assertFalse(User.objects.filter(barbershop=self.a, email__in=['cliente.b@beta.test', 'admin.b@beta.test']).exists())
        lista = self.como(self.admin_a).get('/api/v1/users/').json()['results']
        self.assertTrue(all(u['barbershop'] == self.a.pk for u in lista))
        self.assertEqual(self.cliente_com_token('ADMIN.B@BETA.TEST').get('/api/v1/users/me/').json()['barbershop'], self.b.pk)


class LimitesExistentesTests(TestCase):
    """Com as taxas reais: reenviar o próprio e-mail em outra caixa não gasta a cota da troca de e-mail (mitigação D)."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        loja = Barbershop.objects.create(nome='Alfa', endereco='Rua 1', telefone='1', email='c@alfa.test',
                                         horario_abertura='08:00', horario_fechamento='18:00')
        self.cliente = User.objects.create_user(email='cliente@alfa.test', nome='C', password=SENHA, barbershop=loja)

    def test_proprio_email_em_outra_caixa_nao_consome_cota(self):
        self.assertFalse(tenta_trocar_email({'email': ' CLIENTE@ALFA.TEST '}, self.cliente))
        self.assertTrue(tenta_trocar_email({'email': 'cliente@álfa.test'}, self.cliente))
        c = APIClient()
        c.force_authenticate(self.cliente)
        url = f'/api/v1/users/{self.cliente.pk}/'
        codigos = [c.patch(url, {'nome': f'C {i}', 'email': 'CLIENTE@ALFA.TEST'}, format='json').status_code for i in range(15)]
        self.assertEqual(codigos, [200] * 15)  # acima do limite de 10/hora: nenhuma conta
        codigos = [c.patch(url, {'nome': '', 'email': f'novo{i}@alfa.test'}, format='json').status_code for i in range(11)]
        self.assertEqual(codigos, [400] * 10 + [429])  # a troca real continua limitada


# ---------------------------------------------------------------------------------- PostgreSQL: concorrência
@skipUnless(em_postgresql(), 'concorrência real: só no PostgreSQL')
class ConcorrenciaRealTests(SemLimites, TransactionTestCase):
    """Dois pedidos passam juntos pelo UniqueValidator (barreira) e gravam ao mesmo tempo: o banco decide."""

    def setUp(self):
        super().setUp()
        self.a = Barbershop.objects.create(nome='Alfa', endereco='Rua 1', telefone='1', email='c@alfa.test',
                                           horario_abertura='08:00', horario_fechamento='18:00')
        self.b = Barbershop.objects.create(nome='Beta', endereco='Rua 2', telefone='2', email='c@beta.test',
                                           horario_abertura='08:00', horario_fechamento='18:00')
        self.admin_a = User.objects.create_user(email='admin.a@alfa.test', nome='A', password=SENHA, tipo_perfil='admin', barbershop=self.a)
        self.admin_b = User.objects.create_user(email='admin.b@beta.test', nome='B', password=SENHA, tipo_perfil='admin', barbershop=self.b)
        self.cliente_a = User.objects.create_user(email='cliente.a@alfa.test', nome='CA', password=SENHA, barbershop=self.a)
        self.cliente_b = User.objects.create_user(email='cliente.b@beta.test', nome='CB', password=SENHA, barbershop=self.b)

    def em_paralelo(self, pedidos):
        barreira = threading.Barrier(len(pedidos), timeout=15)
        original = UniqueValidator.__call__

        def validar_e_esperar(validador, valor, campo):
            original(validador, valor, campo)
            if campo.field_name == 'email':
                try:
                    barreira.wait()
                except threading.BrokenBarrierError:
                    pass

        resultados = [None] * len(pedidos)

        def rodar(i, pedido):
            try:
                resultados[i] = pedido()
            finally:
                connection.close()

        with mock.patch.object(UniqueValidator, '__call__', validar_e_esperar):
            threads = [threading.Thread(target=rodar, args=(i, p)) for i, p in enumerate(pedidos)]
            [t.start() for t in threads]
            [t.join(30) for t in threads]
        return resultados

    def cliente(self, usuario=None):
        c = APIClient()
        c.raise_request_exception = False
        if usuario:
            c.force_authenticate(usuario)
        return c

    def conferir(self, resultados, sucesso, email):
        codigos = sorted(r.status_code for r in resultados)
        self.assertEqual(codigos, sorted([sucesso, 400]), [r.content for r in resultados])
        recusado = next(r for r in resultados if r.status_code == 400)
        self.assertEqual(recusado.json(), {'email': [UNICIDADE]})
        self.assertEqual(User.objects.filter(email=email).count(), 1)

    def test_dois_cadastros_publicos_equivalentes(self):
        for i in range(3):
            with self.subTest(rodada=i):
                corpo = lambda e: {'nome': 'X', 'email': e, 'password': SENHA}  # noqa: E731
                r = self.em_paralelo([lambda: self.cliente().post('/api/v1/auth/register/', corpo(f'corrida{i}@exemplo.test'), format='json'),
                                      lambda: self.cliente().post('/api/v1/auth/register/', corpo(f'CORRIDA{i}@EXEMPLO.TEST'), format='json')])
                self.conferir(r, 201, f'corrida{i}@exemplo.test')

    def test_dois_admins_de_barbearias_diferentes(self):
        corpo = {'nome': 'X', 'email': 'Disputado@Exemplo.Test', 'password': SENHA, 'tipo_perfil': 'cliente'}
        r = self.em_paralelo([lambda: self.cliente(self.admin_a).post('/api/v1/users/', corpo, format='json'),
                              lambda: self.cliente(self.admin_b).post('/api/v1/users/', corpo, format='json')])
        self.conferir(r, 201, 'disputado@exemplo.test')

    def test_duas_trocas_de_email_para_o_mesmo(self):
        r = self.em_paralelo([
            lambda: self.cliente(self.cliente_a).patch(f'/api/v1/users/{self.cliente_a.pk}/', {'email': 'Alvo@Exemplo.Test'}, format='json'),
            lambda: self.cliente(self.cliente_b).patch(f'/api/v1/users/{self.cliente_b.pk}/', {'email': 'ALVO@exemplo.test'}, format='json'),
        ])
        self.conferir(r, 200, 'alvo@exemplo.test')


# ------------------------------------------------------------------------- PostgreSQL: equivalência (pt_BR)
@skipUnless(em_postgresql(), 'equivalência Python × PostgreSQL: só no PostgreSQL')
class EquivalenciaPostgreSQLTests(TestCase):
    def setUp(self):
        with connection.cursor() as cur:
            cur.execute('select datctype from pg_database where datname = current_database()')
            self.ctype = cur.fetchone()[0]
        if not self.ctype.startswith('pt_BR'):
            self.skipTest(f'o banco de teste usa {self.ctype}, não pt_BR: a equivalência do banco real não foi reproduzida')

    def test_lower_e_faixa_iguais_em_todo_o_ascii_e_regex_exata_em_todos_os_pontos(self):
        with connection.cursor() as cur:
            cur.execute('select c, lower(chr(c)) from generate_series(1, 127) c')
            self.assertEqual({c: chr(c).lower() for c in range(1, 128)}, dict(cur.fetchall()))
            cur.execute("select count(*) from generate_series(1, 1114111) c where c not between 55296 and 57343 "
                        "and (chr(c) ~ '^[!-~]+$') <> (c between 33 and 126)")
            self.assertEqual(cur.fetchone()[0], 0)

    def test_toda_forma_canonica_satisfaz_o_check_no_banco(self):
        amostras = [forma_canonica(e) for e in ['A@B.TEST', "X!#$%&'*+/=?^_`{|}~-Y@Z.TEST", ' Q@XN--LFA-1LA.TEST ', '9@9.9']]
        amostras += [forma_canonica(f'{chr(c)}x@y.test') for c in range(0x21, 0x7F)]
        with connection.cursor() as cur:
            cur.execute("select count(*) from unnest(%s::text[]) e where not (e = lower(e) and e ~ '^[!-~]+$')", [amostras])
            self.assertEqual(cur.fetchone()[0], 0)


# ---------------------------------------------------------------------------------------------- migração 0006
class MigracaoEmailNormalizadoTests(TransactionTestCase):
    anterior = [('accounts', '0005_protect_barbershop')]
    alvo = [('accounts', '0006_email_normalizado')]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.anterior)
        self.User = executor.loader.project_state(self.anterior).apps.get_model('accounts', 'User')

    def tearDown(self):
        self.User.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def legado(self, email, nome='Conta Antiga'):
        return self.User.objects.create(email=email, nome=nome, password='!', tipo_perfil='cliente').pk

    def migrar(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.alvo)

    def restricoes(self):
        with connection.cursor() as cur:
            return set(connection.introspection.get_constraints(cur, 'accounts_user'))

    def aplicada(self):
        return ('accounts', '0006_email_normalizado') in MigrationRecorder(connection).applied_migrations()

    def test_dados_antigos_validos_sao_convertidos(self):
        ids = {self.legado(e): esperado for e, esperado in [('Pessoa.Dois@exemplo.test', 'pessoa.dois@exemplo.test'),
                                                            ('novo.3@EXEMPLO.TEST', 'novo.3@exemplo.test'),
                                                            ('espaco@exemplo.test ', 'espaco@exemplo.test'),
                                                            ('ja.normal@exemplo.test', 'ja.normal@exemplo.test')]}
        self.migrar()
        self.assertTrue(self.aplicada())
        self.assertEqual({pk: e for pk, e in User.objects.values_list('id', 'email')}, ids)
        self.assertTrue({RESTRICAO_CHECK, RESTRICAO_UNIQUE_LOWER} <= self.restricoes())

    def test_colisoes_interrompem_sem_alterar_nada_e_mostram_so_ids(self):
        a = self.legado('cliente.b@beta.test', 'Clara Cliente B')
        b = self.legado('Cliente.B@beta.test', 'Aaron Variante')
        c = self.legado('espaco@exemplo.test')
        d = self.legado('espaco@exemplo.test ')
        e = self.legado('Outra.Conta@exemplo.test')
        antes = list(self.User.objects.order_by('id').values_list('id', 'email'))
        with self.assertRaises(MIGRACAO.MigracaoDeEmailInterrompida) as ctx:
            self.migrar()
        mensagem = str(ctx.exception)
        self.assertIn(f'[[{a}, {b}], [{c}, {d}]]', mensagem)
        self.assertNotIn('@', mensagem)
        self.assertNotIn('Clara', mensagem)
        self.assertNotIn('Aaron', mensagem)
        self.assertNotIn(str(e), mensagem.split('(ids):')[2])
        self.assertFalse(self.aplicada())
        self.assertEqual(list(self.User.objects.order_by('id').values_list('id', 'email')), antes)
        self.assertFalse({RESTRICAO_CHECK, RESTRICAO_UNIQUE_LOWER} & self.restricoes())

    def test_emails_fora_da_faixa_interrompem(self):
        bons = [self.legado('bom@exemplo.test')]
        ruins = [self.legado('joão@exemplo.test'), self.legado('x@álfa.test'), self.legado('x@exem​plo.test'),
                 self.legado('com espaco@exemplo.test'), self.legado('')]
        antes = list(self.User.objects.order_by('id').values_list('id', 'email'))
        with self.assertRaises(MIGRACAO.MigracaoDeEmailInterrompida) as ctx:
            self.migrar()
        self.assertIn(f'(ids): {ruins}', str(ctx.exception))
        self.assertNotIn(str(bons[0]) + ',', str(ctx.exception).split('(ids):')[1].split('.')[0])
        self.assertNotIn('@', str(ctx.exception))
        self.assertFalse(self.aplicada())
        self.assertEqual(list(self.User.objects.order_by('id').values_list('id', 'email')), antes)

    def test_reversao_retira_as_restricoes_e_nao_recupera_a_grafia_original(self):
        pk = self.legado('Grafia.Original@Exemplo.TEST')
        self.migrar()
        self.assertEqual(User.objects.get(pk=pk).email, 'grafia.original@exemplo.test')
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.anterior)
        self.assertFalse(self.aplicada())
        self.assertFalse({RESTRICAO_CHECK, RESTRICAO_UNIQUE_LOWER} & self.restricoes())
        self.assertEqual(self.User.objects.get(pk=pk).email, 'grafia.original@exemplo.test')  # a grafia original não volta
