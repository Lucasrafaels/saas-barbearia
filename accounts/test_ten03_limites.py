"""
TEN-03, mitigação D: limites de tentativas nas operações que consultam a unicidade do e-mail.

A investigação (seção 26 do relatório) mostrou três fluxos em que a resposta revela se um e-mail já existe em
qualquer barbearia: o cadastro público (anônimo), a criação de usuários pelo administrador e a troca de e-mail
(qualquer papel, na própria conta, ou o admin nas contas da sua barbearia). Estes testes garantem que:

- cada fluxo tem um limite próprio, por hora e por dia, e que, esgotado, a resposta é 429 **antes** da validação:
  igual para e-mail existente e livre, sem consultar a unicidade e sem criar nem alterar nada;
- a cota é de quem pede (conta ou origem), nunca do e-mail-alvo: um terceiro não bloqueia a vítima;
- uso legítimo (cadastro, criação, edição sem troca de e-mail, reenvio do próprio e-mail) não é bloqueado;
- login e recuperação de senha continuam com os mesmos limites e respostas;
- o 429 não revela nada a mais, com DEBUG True ou False.

Não testam que o oráculo acabou: abaixo do limite ele continua (o TEN-03 segue aberto; a correção é a C3).
Dados fictícios (domínios .test).
"""
from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

import config.settings as settings_de_producao
from accounts.models import User
from accounts.throttles import (
    CadastroPublicoPorDiaThrottle,
    CriacaoDeUsuarioPorDiaThrottle,
    CriacaoDeUsuarioPorHoraThrottle,
    TrocaDeEmailPorDiaThrottle,
    TrocaDeEmailPorHoraThrottle,
    tenta_trocar_email,
)
from accounts.views import (
    CustomTokenObtainPairView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegistrationView,
    ThrottledTokenRefreshView,
    UserViewSet,
)
from barbershops.models import Barbershop

SENHA = 'Senha-Ficticia-2026!'
SENHA_FRACA = '12345678'  # passa no min_length e cai nos validadores: a tentativa não cria nada
NOVAS_TAXAS = {
    'register_day': '20/day',
    'user_create': '30/hour',
    'user_create_day': '100/day',
    'email_change': '10/hour',
    'email_change_day': '30/day',
}
TAXAS_QUE_NAO_MUDARAM = {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '5/minute',
    'register': '10/hour',
    'refresh': '10/minute',
    'logout': '30/minute',
    'password_change': '5/hour',
    'password_reset': '5/hour',
    'password_reset_confirm': '10/hour',
}


def consultou_unicidade(contexto):
    """A consulta do UniqueValidator procura a conta pelo e-mail (com ou sem `AND NOT id = …`)."""
    return any('"accounts_user"."email" =' in q['sql'] and 'SELECT 1' in q['sql'] for q in contexto.captured_queries)


class BaseLimites(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        # Relógio dos limites parado: o "Retry-After" não varia entre respostas, e as janelas só andam quando o
        # teste avança o relógio de propósito.
        relogio = mock.patch.object(SimpleRateThrottle, 'timer', mock.Mock(return_value=1_000_000.0))
        relogio.start()
        self.addCleanup(relogio.stop)
        self.shop_a =self._barbearia('Alfa Fictícia', 'contato@alfa.test')
        self.shop_b = self._barbearia('Beta Fictícia', 'contato@beta.test')
        self.admin_a = self._user('admin.a@alfa.test', 'Ana Admin A', 'admin', self.shop_a)
        self.admin_a2 = self._user('admin2.a@alfa.test', 'Alice Admin A2', 'admin', self.shop_a)
        self.cliente_a1 = self._user('cliente.a1@alfa.test', 'Carlos Cliente A1', 'cliente', self.shop_a)
        self.cliente_a2 = self._user('cliente.a2@alfa.test', 'Celia Cliente A2', 'cliente', self.shop_a)
        self.admin_b = self._user('admin.b@beta.test', 'Beatriz Admin B', 'admin', self.shop_b)
        self.cliente_b = self._user('cliente.b@beta.test', 'Clara Cliente B', 'cliente', self.shop_b)
        self.existente = self.cliente_b.email
        self.contador = 0

    @staticmethod
    def _barbearia(nome, email):
        return Barbershop.objects.create(nome=nome, endereco='Rua Exemplo, 1', telefone='11900000000', email=email,
                                         horario_abertura='09:00', horario_fechamento='19:00')

    @staticmethod
    def _user(email, nome, perfil, shop):
        return User.objects.create_user(email=email, nome=nome, password=SENHA, tipo_perfil=perfil, barbershop=shop)

    def livre(self):
        self.contador += 1
        return f'livre.{self.contador}@exemplo.test'

    def como(self, usuario):
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return cliente

    def url_usuario(self, usuario):
        return reverse('user-detail', args=[usuario.pk])

    def assert_429_sem_validar(self, enviar, emails):
        """Cada envio responde 429, sem consultar a unicidade; as respostas são idênticas entre si."""
        corpos = []
        total = User.objects.count()
        for email in emails:
            with CaptureQueriesContext(connection) as ctx:
                resposta = enviar(email)
            self.assertEqual(resposta.status_code, status.HTTP_429_TOO_MANY_REQUESTS, resposta.content)
            self.assertFalse(consultou_unicidade(ctx), 'o 429 não pode consultar a unicidade do e-mail')
            self.assertIn('Retry-After', resposta.headers)
            self.assertEqual(set(resposta.json()), {'detail'})
            self.assertNotIn(email.strip(), resposta.content.decode())
            corpos.append((resposta.content, resposta.headers['Retry-After']))
        self.assertEqual(len(set(corpos)), 1, 'existente e livre precisam receber o mesmo 429')
        self.assertEqual(User.objects.count(), total)


class ConfiguracaoDosLimitesTests(BaseLimites):
    def test_taxas_novas_em_producao_e_nos_testes(self):
        producao = settings_de_producao.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        for escopo, taxa in NOVAS_TAXAS.items():
            with self.subTest(escopo=escopo):
                self.assertEqual(producao[escopo], taxa)
                self.assertEqual(SimpleRateThrottle.THROTTLE_RATES[escopo], taxa)

    def test_taxas_que_ja_existiam_nao_mudaram(self):
        producao = settings_de_producao.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        for escopo, taxa in TAXAS_QUE_NAO_MUDARAM.items():
            with self.subTest(escopo=escopo):
                self.assertEqual(producao[escopo], taxa)
        self.assertEqual(
            settings_de_producao.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'],
            ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
        )

    def test_login_recuperacao_e_sessao_mantem_os_limites(self):
        for view, escopo in [(CustomTokenObtainPairView, 'login'), (PasswordResetRequestView, 'password_reset'),
                             (PasswordResetConfirmView, 'password_reset_confirm'), (ThrottledTokenRefreshView, 'refresh'),
                             (PasswordChangeView, 'password_change'), (LogoutView, 'logout')]:
            with self.subTest(view=view.__name__):
                self.assertEqual(view.throttle_classes, [ScopedRateThrottle])
                self.assertEqual(view.throttle_scope, escopo)

    def test_cadastro_tem_o_limite_por_hora_e_o_diario(self):
        self.assertEqual(RegistrationView.throttle_scope, 'register')
        self.assertEqual(RegistrationView.throttle_classes, [ScopedRateThrottle, CadastroPublicoPorDiaThrottle])

    def test_limites_da_criacao_so_na_acao_create(self):
        for acao, esperados in [('create', {CriacaoDeUsuarioPorHoraThrottle, CriacaoDeUsuarioPorDiaThrottle}),
                                ('list', set()), ('retrieve', set()), ('partial_update', set()), ('me', set())]:
            with self.subTest(acao=acao):
                view = UserViewSet()
                view.action = acao
                novos = {type(t) for t in view.get_throttles()} - {type(t) for t in super(UserViewSet, view).get_throttles()}
                self.assertEqual(novos, esperados)

    def test_chave_e_quem_pede_nunca_o_email(self):
        fabrica = APIRequestFactory()
        anonimo = fabrica.post('/', {'email': self.existente}, format='json', REMOTE_ADDR='10.1.2.3')
        anonimo.user = mock.Mock(is_authenticated=False)
        chave = CadastroPublicoPorDiaThrottle().get_cache_key(anonimo, None)
        self.assertEqual(chave, 'throttle_register_day_10.1.2.3')
        autenticado = fabrica.patch('/', {'email': self.existente}, format='json')
        autenticado.user = self.cliente_a1
        for classe, escopo in [(TrocaDeEmailPorHoraThrottle, 'email_change'), (TrocaDeEmailPorDiaThrottle, 'email_change_day'),
                               (CriacaoDeUsuarioPorHoraThrottle, 'user_create'), (CriacaoDeUsuarioPorDiaThrottle, 'user_create_day')]:
            with self.subTest(escopo=escopo):
                chave = classe().get_cache_key(autenticado, None)
                self.assertEqual(chave, f'throttle_{escopo}_{self.cliente_a1.pk}')
                self.assertNotIn('beta.test', chave)

    def test_o_que_conta_como_troca_de_email(self):
        conta = self.cliente_a1
        casos = [
            ({'email': 'outro@exemplo.test'}, True),
            ({'email': self.existente}, True),
            ({'email': 'Cliente.A1@alfa.test'}, False),       # AUTH-05: outra caixa é o mesmo e-mail canônico
            ({'email': ' CLIENTE.A1@ALFA.TEST '}, False),     # idem, com espaços externos
            ({'email': 'cliente.a1@álfa.test'}, True),        # fora da regra: o serializer recusa, e conta como antes
            ({'email': None}, True),
            ({'email': conta.email}, False),
            ({'email': f'  {conta.email}  '}, False),           # o EmailField corta os espaços
            ({'nome': 'Novo Nome'}, False),
            ({'nome': 'Novo Nome', 'email': conta.email}, False),  # o que "Minha conta" e "Clientes" enviam
            ({'is_active': False}, False),
            ({}, False),
            ([{'email': 'x@exemplo.test'}], False),             # corpo que não é objeto: o serializer recusa
        ]
        for dados, esperado in casos:
            with self.subTest(dados=dados):
                self.assertIs(tenta_trocar_email(dados, conta), esperado)


class CadastroPublicoTests(BaseLimites):
    url = reverse('auth-register')

    def enviar(self, email, senha=SENHA_FRACA, ip='10.0.0.1'):
        return self.client.post(self.url, {'nome': 'Pessoa Fictícia', 'email': email, 'password': senha},
                                format='json', REMOTE_ADDR=ip)

    def test_antes_do_limite_valida_e_depois_responde_429_sem_validar(self):
        for indice in range(10):  # 'register': 10/hour (já existia)
            email = self.existente if indice % 2 else self.livre()
            resposta = self.enviar(email)
            self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST, (indice, resposta.content))
        self.assert_429_sem_validar(self.enviar, [self.existente, self.livre(), f'  {self.existente}  '])

    def test_limite_diario(self):
        with mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'register': '1000/hour', 'register_day': '3/day'}):
            for _ in range(3):
                self.assertEqual(self.enviar(self.livre()).status_code, status.HTTP_400_BAD_REQUEST)
            self.assert_429_sem_validar(self.enviar, [self.existente, self.livre()])

    def test_origens_independentes_e_cadastro_legitimo(self):
        for _ in range(10):
            self.enviar(self.livre(), ip='10.0.0.1')
        self.assertEqual(self.enviar(self.livre(), ip='10.0.0.1').status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        email = self.livre()
        resposta = self.enviar(email, senha=SENHA, ip='10.0.0.2')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.content)
        self.assertTrue(User.objects.filter(email=email).exists())
        login = self.client.post(reverse('token_obtain_pair'), {'email': email, 'password': SENHA}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_a_janela_expira(self):
        relogio = mock.Mock(return_value=1_000_000.0)
        with mock.patch.object(SimpleRateThrottle, 'timer', relogio):
            for _ in range(10):
                self.enviar(self.livre())
            self.assertEqual(self.enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            relogio.return_value += 3601
            resposta = self.enviar(self.livre(), senha=SENHA)
            self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.content)


class CriacaoDeUsuarioTests(BaseLimites):
    url = reverse('user-list')

    def enviar_como(self, usuario, senha=SENHA_FRACA):
        cliente = self.como(usuario)
        return lambda email: cliente.post(self.url, {'nome': 'Cliente Fictício', 'email': email, 'password': senha,
                                                     'tipo_perfil': 'cliente'}, format='json')

    def test_antes_do_limite_valida_e_depois_responde_429_sem_validar(self):
        enviar = self.enviar_como(self.admin_a)
        for indice in range(30):  # 'user_create': 30/hour
            email = self.existente if indice % 2 else self.livre()
            self.assertEqual(enviar(email).status_code, status.HTTP_400_BAD_REQUEST, indice)
        self.assert_429_sem_validar(enviar, [self.existente, self.livre(), self.cliente_a2.email])

    def test_limite_diario(self):
        with mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'user_create': '1000/hour', 'user_create_day': '2/day'}):
            enviar = self.enviar_como(self.admin_a)
            for _ in range(2):
                self.assertEqual(enviar(self.livre()).status_code, status.HTTP_400_BAD_REQUEST)
            self.assert_429_sem_validar(enviar, [self.existente, self.livre()])

    def test_cota_por_administrador_e_criacao_legitima(self):
        enviar = self.enviar_como(self.admin_a)
        for _ in range(30):
            enviar(self.livre())
        self.assertEqual(enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        for admin in (self.admin_a2, self.admin_b):  # outro admin da mesma barbearia e de outra
            with self.subTest(admin=admin.email):
                email = self.livre()
                resposta = self.enviar_como(admin, senha=SENHA)(email)
                self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.content)
                criado = User.objects.get(email=email)
                self.assertEqual(criado.barbershop_id, admin.barbershop_id)
                login = self.client.post(reverse('token_obtain_pair'), {'email': email, 'password': SENHA}, format='json')
                self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_cliente_e_conta_sem_barbearia_continuam_com_403_e_nao_gastam_cota(self):
        sem_barbearia = User.objects.create_user(email='sem.barbearia@exemplo.test', nome='Saulo', password=SENHA)
        for usuario in (self.cliente_a1, sem_barbearia):
            enviar = self.enviar_como(usuario)
            with self.subTest(usuario=usuario.email):
                for _ in range(35):
                    self.assertEqual(enviar(self.existente).status_code, status.HTTP_403_FORBIDDEN)

    def test_a_janela_expira(self):
        relogio = mock.Mock(return_value=2_000_000.0)
        with mock.patch.object(SimpleRateThrottle, 'timer', relogio):
            enviar = self.enviar_como(self.admin_a)
            for _ in range(30):
                enviar(self.livre())
            self.assertEqual(enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            relogio.return_value += 3601
            self.assertEqual(self.enviar_como(self.admin_a, senha=SENHA)(self.livre()).status_code, status.HTTP_201_CREATED)


class TrocaDeEmailTests(BaseLimites):
    def patch_como(self, usuario, alvo=None, extra=None):
        cliente = self.como(usuario)
        url = self.url_usuario(alvo or usuario)
        return lambda email: cliente.patch(url, {'email': email, **(extra or {})}, format='json')

    def esgotar(self, enviar, vezes=10):
        for _ in range(vezes):
            self.assertNotEqual(enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_antes_do_limite_valida_e_depois_responde_429_sem_validar(self):
        # Pedidos sem efeito colateral (nome vazio): só a validação responde.
        enviar = self.patch_como(self.cliente_a1, extra={'nome': ''})
        for indice in range(10):  # 'email_change': 10/hour
            email = self.existente if indice % 2 else self.livre()
            self.assertEqual(enviar(email).status_code, status.HTTP_400_BAD_REQUEST, indice)
        self.assert_429_sem_validar(enviar, [self.existente, self.livre(), self.cliente_a2.email])
        self.cliente_a1.refresh_from_db()
        self.assertEqual(self.cliente_a1.email, 'cliente.a1@alfa.test')

    def test_put_e_patch_dividem_a_mesma_cota(self):
        cliente = self.como(self.cliente_a1)
        url = self.url_usuario(self.cliente_a1)
        for indice in range(10):
            corpo = {'email': self.livre(), 'nome': 'Carlos Cliente A1'}
            resposta = cliente.put(url, corpo, format='json') if indice % 2 else cliente.patch(url, corpo, format='json')
            self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.content)
        self.assert_429_sem_validar(
            lambda email: cliente.put(url, {'email': email, 'nome': 'Carlos Cliente A1'}, format='json'),
            [self.existente, self.livre()],
        )

    def test_limite_diario(self):
        with mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'email_change': '1000/hour', 'email_change_day': '2/day'}):
            enviar = self.patch_como(self.cliente_a1, extra={'nome': ''})
            self.esgotar(enviar, vezes=2)
            self.assert_429_sem_validar(enviar, [self.existente, self.livre()])

    def test_edicoes_sem_troca_de_email_nao_contam_nem_sao_bloqueadas(self):
        cliente = self.como(self.cliente_a1)
        url = self.url_usuario(self.cliente_a1)
        for indice in range(25):  # bem acima do limite: nenhuma conta
            self.assertEqual(cliente.patch(url, {'nome': f'Carlos {indice}'}, format='json').status_code, status.HTTP_200_OK)
            self.assertEqual(cliente.patch(url, {'nome': 'Carlos', 'email': self.cliente_a1.email}, format='json').status_code,
                             status.HTTP_200_OK)
        self.esgotar(self.patch_como(self.cliente_a1), vezes=10)  # a cota inteira continua disponível
        self.cliente_a1.refresh_from_db()
        atual = self.cliente_a1.email
        self.assertEqual(cliente.patch(url, {'email': self.livre()}, format='json').status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Esgotada a cota, o que não troca o e-mail continua funcionando.
        for corpo in ({'nome': 'Carlos Final'}, {'nome': 'Carlos Final', 'email': atual}, {'email': f'  {atual}  '}):
            with self.subTest(corpo=corpo):
                self.assertEqual(cliente.patch(url, corpo, format='json').status_code, status.HTTP_200_OK)
        self.assertEqual(cliente.get(reverse('user-me')).status_code, status.HTTP_200_OK)

    def test_admin_gasta_a_propria_cota_e_nao_a_do_cliente_editado(self):
        self.esgotar(self.patch_como(self.admin_a, alvo=self.cliente_a1))
        self.assertEqual(self.patch_como(self.admin_a, alvo=self.cliente_a1)(self.livre()).status_code,
                         status.HTTP_429_TOO_MANY_REQUESTS)
        # A cota é do admin A: o cliente editado e o outro admin não foram afetados.
        self.assertEqual(self.patch_como(self.cliente_a1)(self.livre()).status_code, status.HTTP_200_OK)
        self.assertEqual(self.patch_como(self.admin_a2, alvo=self.cliente_a1)(self.livre()).status_code, status.HTTP_200_OK)
        # O admin A continua editando o que não é e-mail, inclusive reativar.
        cliente = self.como(self.admin_a)
        url = self.url_usuario(self.cliente_a2)
        self.assertEqual(cliente.patch(url, {'is_active': False}, format='json').status_code, status.HTTP_200_OK)
        self.assertEqual(cliente.patch(url, {'is_active': True}, format='json').status_code, status.HTTP_200_OK)

    def test_terceiro_nao_bloqueia_a_vitima(self):
        # O cliente A1 sonda repetidamente o e-mail da cliente B até ser limitado.
        tentativa = self.patch_como(self.cliente_a1, extra={'nome': ''})
        for _ in range(15):
            tentativa(self.existente)
        self.assertEqual(tentativa(self.existente).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # A vítima não perdeu nada: troca o próprio e-mail, entra e pede recuperação de senha.
        novo = self.livre()
        self.assertEqual(self.patch_como(self.cliente_b)(novo).status_code, status.HTTP_200_OK)
        login = self.client.post(reverse('token_obtain_pair'), {'email': novo, 'password': SENHA}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(reverse('password_reset'), {'email': novo}, format='json').status_code,
                         status.HTTP_204_NO_CONTENT)

    def test_fora_do_alcance_mantem_a_resposta_e_nao_gasta_cota(self):
        casos = [
            (self.admin_a, self.cliente_b, status.HTTP_404_NOT_FOUND),       # outra barbearia
            (self.cliente_a1, self.cliente_a2, status.HTTP_403_FORBIDDEN),   # mesma barbearia (SEC-12, mantido)
        ]
        for solicitante, alvo, esperado in casos:
            with self.subTest(solicitante=solicitante.email):
                enviar = self.patch_como(solicitante, alvo=alvo)
                for _ in range(15):
                    self.assertEqual(enviar(self.livre()).status_code, esperado)
                self.esgotar(self.patch_como(solicitante, alvo=solicitante))  # a cota inteira continua lá
        sem_barbearia = User.objects.create_user(email='sem.barbearia@exemplo.test', nome='Saulo', password=SENHA)
        enviar = self.patch_como(sem_barbearia)
        for _ in range(15):
            self.assertEqual(enviar(self.existente).status_code, status.HTTP_404_NOT_FOUND)

    def test_a_janela_expira(self):
        relogio = mock.Mock(return_value=3_000_000.0)
        with mock.patch.object(SimpleRateThrottle, 'timer', relogio):
            enviar = self.patch_como(self.cliente_a1)
            self.esgotar(enviar)
            self.assertEqual(enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            relogio.return_value += 3601
            self.assertEqual(enviar(self.livre()).status_code, status.HTTP_200_OK)


class RespostaDoLimiteTests(BaseLimites):
    """O 429 é o mesmo para e-mail existente e livre e não revela nada, com DEBUG True ou False."""

    def cenarios(self):
        anonimo = APIClient()
        admin = self.como(self.admin_a)
        cliente = self.como(self.cliente_a1)
        return [
            ('cadastro público', 10, lambda e: anonimo.post(reverse('auth-register'), {
                'nome': 'Pessoa', 'email': e, 'password': SENHA_FRACA}, format='json')),
            ('criação de usuário', 30, lambda e: admin.post(reverse('user-list'), {
                'nome': 'Pessoa', 'email': e, 'password': SENHA_FRACA, 'tipo_perfil': 'cliente'}, format='json')),
            ('troca de e-mail', 10, lambda e: cliente.patch(self.url_usuario(self.cliente_a1), {
                'nome': '', 'email': e}, format='json')),
        ]

    def test_429_identico_e_sem_dados_com_debug_true_e_false(self):
        for debug in (True, False):
            for nome, limite, enviar in self.cenarios():
                with self.subTest(debug=debug, fluxo=nome), override_settings(DEBUG=debug), \
                        mock.patch.object(SimpleRateThrottle, 'timer', mock.Mock(return_value=4_000_000.0)):
                    cache.clear()
                    for _ in range(limite):
                        self.assertNotEqual(enviar(self.livre()).status_code, status.HTTP_429_TOO_MANY_REQUESTS)
                    self.assert_429_sem_validar(enviar, [self.existente, self.livre(), self.cliente_a2.email, 'nao-e-email'])
                    resposta = enviar(self.existente)
                    self.assertEqual(resposta['Content-Type'], 'application/json')
                    self.assertEqual(resposta['Retry-After'], '3600')
                    self.assertNotIn(b'<html', resposta.content.lower())
                    for proibido in (b'beta', b'alfa', b'barbershop', b'email', b'Traceback'):
                        self.assertNotIn(proibido, resposta.content)


class LoginERecuperacaoPreservadosTests(BaseLimites):
    """Esgotar os limites novos não afeta login nem recuperação, que mantêm as mesmas respostas e limites."""

    def esgotar_tudo(self):
        for _ in range(11):
            self.client.post(reverse('auth-register'), {'nome': 'X', 'email': self.livre(), 'password': SENHA_FRACA},
                             format='json')
        cliente = self.como(self.cliente_a1)
        for _ in range(11):
            cliente.patch(self.url_usuario(self.cliente_a1), {'nome': '', 'email': self.livre()}, format='json')
        admin = self.como(self.admin_a)
        for _ in range(31):
            admin.post(reverse('user-list'), {'nome': 'X', 'email': self.livre(), 'password': SENHA_FRACA,
                                              'tipo_perfil': 'cliente'}, format='json')

    def test_login_e_recuperacao_depois_de_esgotar_os_limites_novos(self):
        self.esgotar_tudo()
        login = reverse('token_obtain_pair')
        for usuario in (self.cliente_a1, self.admin_a):
            with self.subTest(usuario=usuario.email):
                resposta = self.client.post(login, {'email': usuario.email, 'password': SENHA}, format='json')
                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertIn('access', resposta.json())
        errado =self.client.post(login, {'email': self.existente, 'password': 'Errada-123!'}, format='json')
        inexistente = self.client.post(login, {'email': self.livre(), 'password': 'Errada-123!'}, format='json')
        self.assertEqual(errado.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(errado.content, inexistente.content)
        reset = reverse('password_reset')
        existente = self.client.post(reset, {'email': self.existente}, format='json')
        livre = self.client.post(reset, {'email': self.livre()}, format='json')
        self.assertEqual((existente.status_code, existente.content), (status.HTTP_204_NO_CONTENT, b''))
        self.assertEqual((livre.status_code, livre.content), (status.HTTP_204_NO_CONTENT, b''))

    def test_o_limite_do_login_continua_o_mesmo(self):
        login = reverse('token_obtain_pair')
        codigos = [self.client.post(login, {'email': self.existente, 'password': 'Errada-123!'}, format='json').status_code
                   for _ in range(6)]  # 'login': 5/minute
        self.assertEqual(codigos, [401] * 5 + [429])

    def test_troca_de_senha_nao_e_afetada(self):
        self.esgotar_tudo()
        cliente = self.como(self.cliente_a1)
        resposta = cliente.post(reverse('password_change'),
                                {'old_password': SENHA, 'new_password': 'Outra-Senha-Ficticia-2026!'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
