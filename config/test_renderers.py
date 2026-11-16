"""
TEN-01 (P0): a API navegável do DRF não pode voltar a ser entregue.

Antes da contenção, as mesmas URLs da API respondiam em HTML quando o pedido
trazia ``Accept: text/html``, ``?format=api`` ou o sufixo ``.api``. Os
``<select>`` dos formulários dessa página listavam clientes, barbeiros,
administradores e serviços de todas as barbearias, inclusive para uma conta
recém-criada no cadastro público (seção 20 de docs/AUDITORIA_BARBERPRO.md).
A contenção deixa só o ``JSONRenderer`` em
``REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']``.

Os testes pedem a representação HTML em todas as rotas da API, com cada papel,
e conferem que nenhuma resposta é HTML nem traz dados. Também conferem que o
JSON, a autenticação e as permissões continuam como antes, que o fluxo do
frontend (axios) segue funcionando e que nenhuma view registrada reativa um
renderizador HTML.
"""
import json
from datetime import time, timedelta

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service

SENHA = 'Senha-segura-123'

# Cabeçalho Accept que o axios envia por padrão (frontend/src/api/client.ts
# não o altera) e o que um navegador envia ao abrir a URL diretamente.
ACCEPT_AXIOS = 'application/json, text/plain, */*'
ACCEPT_NAVEGADOR = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

PAPEIS = (
    'anonimo', 'cliente_a', 'barbeiro_a', 'admin_a',
    'sem_barbearia', 'admin_c', 'superusuario',
)

# Grupo de dados a que cada papel pertence. O superusuário (operador da
# plataforma) vê todas as barbearias por desenho, então só as respostas HTML
# são conferidas para ele.
GRUPO_DO_PAPEL = {
    'anonimo': None,
    'cliente_a': 'A',
    'barbeiro_a': 'A',
    'admin_a': 'A',
    'sem_barbearia': 'SEM',
    'admin_c': 'C',
    'superusuario': 'PLATAFORMA',
}

# Textos fictícios que identificam cada grupo. Na API navegável, os <option>
# exibiam ``User.__str__`` (nome e papel), ``Barber.__str__`` (nome e
# barbearia) e ``Service.__str__`` (nome e barbearia).
MARCAS = {
    'A': (
        'Barbearia Alfa Ficticia', 'Alice Admin Alfa', 'Arthur Barbeiro Alfa',
        'Amanda Cliente Alfa', 'Servico Corte Alfa', '@alfa.test',
    ),
    'B': (
        'Barbearia Beta Ficticia', 'Beatriz Admin Beta', 'Bento Barbeiro Beta',
        'Bruno Barbeiro Inativo Beta', 'Clara Cliente Beta', 'Servico Corte Beta',
        'Servico Inativo Beta', '@beta.test',
    ),
    'C': ('Barbearia Gama Onboarding', 'Gabriela Gama', '@gama.test'),
    'SEM': ('Sergio Sem Barbearia', '@sem.test'),
    'PLATAFORMA': ('Operador Plataforma Teste', '@plataforma.test'),
}
ROTULOS_DE_PAPEL = ('(Administrador)', '(Barbeiro)', '(Cliente)')
TODAS_AS_MARCAS = tuple(m for grupo in MARCAS.values() for m in grupo) + ROTULOS_DE_PAPEL

# Pedidos que, antes da contenção, recebiam a API navegável em HTML.
# nome: (Accept, ?format=, sufixo de formato, status observado após a contenção)
# O DRF negocia o formato antes de autenticar: sem renderizador HTML, o
# Accept só com HTML recebe 406 e o formato "api" pedido na URL recebe 404,
# para qualquer papel, inclusive o anônimo.
VARIANTES_HTML = {
    'Accept: text/html': ('text/html', None, None, 406),
    'Accept: text/html,application/xhtml+xml': ('text/html,application/xhtml+xml', None, None, 406),
    '?format=api': ('*/*', 'api', None, 404),
    '?format=api com Accept: text/html': ('text/html', 'api', None, 404),
    'sufixo .api': ('*/*', None, 'api', 404),
}

# Pedidos legítimos, que devem continuar recebendo JSON com o status de antes.
VARIANTES_JSON = {
    'Accept: application/json': ('application/json', None, None),
    'Accept padrão do axios': (ACCEPT_AXIOS, None, None),
    'Accept de navegador': (ACCEPT_NAVEGADOR, None, None),
    'sem Accept': (None, None, None),
    '?format=json': ('*/*', 'json', None),
    'sufixo .json': ('*/*', None, 'json'),
}


def com_sufixo(caminho, formato):
    """Rota com sufixo de formato, como o DefaultRouter registra."""
    if caminho == '/api/v1/':
        return f'/api/v1/.{formato}'
    return f'{caminho.rstrip("/")}.{formato}'


class Ten01Cenario(APITestCase):
    """Barbearias A e B, conta do cadastro público, barbearia C do onboarding e superusuário."""

    @classmethod
    def setUpTestData(cls):
        cls.shop_a = cls.criar_barbearia('Barbearia Alfa Ficticia', 'contato@alfa.test')
        cls.shop_b = cls.criar_barbearia('Barbearia Beta Ficticia', 'contato@beta.test')

        cls.admin_a = cls.criar_usuario('alice@alfa.test', 'Alice Admin Alfa', 'admin', cls.shop_a)
        cls.cliente_a = cls.criar_usuario('amanda@alfa.test', 'Amanda Cliente Alfa', 'cliente', cls.shop_a)
        barbeiro_user_a = cls.criar_usuario('arthur@alfa.test', 'Arthur Barbeiro Alfa', 'barbeiro', cls.shop_a)
        cls.barber_a = Barber.objects.create(user=barbeiro_user_a, barbershop=cls.shop_a)
        cls.service_a = Service.objects.create(
            barbershop=cls.shop_a, nome='Servico Corte Alfa', preco='50.00', duracao=30,
        )

        cls.criar_usuario('beatriz@beta.test', 'Beatriz Admin Beta', 'admin', cls.shop_b)
        cliente_b = cls.criar_usuario('clara@beta.test', 'Clara Cliente Beta', 'cliente', cls.shop_b)
        barber_b = Barber.objects.create(
            user=cls.criar_usuario('bento@beta.test', 'Bento Barbeiro Beta', 'barbeiro', cls.shop_b),
            barbershop=cls.shop_b,
        )
        Barber.objects.create(
            user=cls.criar_usuario('bruno@beta.test', 'Bruno Barbeiro Inativo Beta', 'barbeiro', cls.shop_b),
            barbershop=cls.shop_b,
            ativo=False,
        )
        service_b = Service.objects.create(
            barbershop=cls.shop_b, nome='Servico Corte Beta', preco='60.00', duracao=30,
        )
        Service.objects.create(
            barbershop=cls.shop_b, nome='Servico Inativo Beta', preco='70.00', duracao=30, ativo=False,
        )
        User.objects.create_superuser(
            email='operador@plataforma.test', nome='Operador Plataforma Teste', password=SENHA,
        )

        cls.inicio = (timezone.localtime() + timedelta(days=2)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        cls.appointment_a = Appointment.objects.create(
            barbershop=cls.shop_a, cliente=cls.cliente_a, barbeiro=cls.barber_a,
            servico=cls.service_a, data_hora=cls.inicio,
        )
        Appointment.objects.create(
            barbershop=cls.shop_b, cliente=cliente_b, barbeiro=barber_b,
            servico=service_b, data_hora=cls.inicio,
        )

        # A conta sem barbearia e a barbearia C nascem pelos fluxos públicos
        # reais, como na auditoria: cadastro e onboarding pela própria API.
        frontend = APIClient()
        for email, nome in (('sergio@sem.test', 'Sergio Sem Barbearia'), ('gabriela@gama.test', 'Gabriela Gama')):
            cache.clear()
            resposta = frontend.post(
                '/api/v1/auth/register/', {'email': email, 'nome': nome, 'password': SENHA},
                format='json', HTTP_ACCEPT=ACCEPT_AXIOS,
            )
            if resposta.status_code != 201:
                raise AssertionError(f'cadastro público de {email}: {resposta.status_code}')
        token_gama = cls.login('gabriela@gama.test')
        resposta = frontend.post(
            '/api/v1/barbershops/',
            {
                'nome': 'Barbearia Gama Onboarding', 'endereco': 'Rua Gama, 3',
                'telefone': '11977777777', 'email': 'contato@gama.test',
                'horario_abertura': '08:00', 'horario_fechamento': '18:00',
            },
            format='json', HTTP_ACCEPT=ACCEPT_AXIOS, HTTP_AUTHORIZATION=f'Bearer {token_gama}',
        )
        if resposta.status_code != 201:
            raise AssertionError(f'onboarding da barbearia C: {resposta.status_code}')

        # Autenticação real: tokens emitidos pelo endpoint de login da API.
        cls.tokens = {
            'cliente_a': cls.login('amanda@alfa.test'),
            'barbeiro_a': cls.login('arthur@alfa.test'),
            'admin_a': cls.login('alice@alfa.test'),
            'sem_barbearia': cls.login('sergio@sem.test'),
            'admin_c': cls.login('gabriela@gama.test'),
            'superusuario': cls.login('operador@plataforma.test'),
        }

    @staticmethod
    def criar_barbearia(nome, email):
        return Barbershop.objects.create(
            nome=nome, endereco='Rua dos Testes, 100', telefone='11999999999', email=email,
            horario_abertura=time(8), horario_fechamento=time(18),
        )

    @staticmethod
    def criar_usuario(email, nome, perfil, barbearia):
        return User.objects.create_user(
            email=email, nome=nome, password=SENHA, tipo_perfil=perfil, barbershop=barbearia,
        )

    @staticmethod
    def login(email):
        # O login tem limite próprio (ScopedRateThrottle, 5/minuto), que não
        # é o assunto destes testes.
        cache.clear()
        resposta = APIClient().post(
            '/api/v1/auth/login/', {'email': email, 'password': SENHA},
            format='json', HTTP_ACCEPT=ACCEPT_AXIOS,
        )
        if resposta.status_code != 200:
            raise AssertionError(f'login de {email}: {resposta.status_code}')
        return resposta.json()['access']

    def rotas(self):
        """
        Todas as rotas da API (GET): nome, caminho, consulta, sufixos de formato
        registrados e o status JSON de cada papel, na ordem de PAPEIS. Os status
        são os da API antes da contenção: a contenção não pode mudar nenhum.

        Sufixos: o DefaultRouter registra "<rota>.<formato>" para as rotas dos
        ViewSets ("rota") e das @action ("acao"); as views de autenticação não
        têm sufixo (None). Nas @action, o sufixo ".json" já respondia 500 antes
        da contenção, porque os métodos não aceitam o argumento "format"
        (API-03, fora do escopo do TEN-01); por isso só o ".api" é pedido nelas.
        """
        dia = self.inicio.date().isoformat()
        return (
            ('raiz da API', '/api/v1/', {}, 'rota', (401, 200, 200, 200, 200, 200, 200)),
            ('usuários', '/api/v1/users/', {}, 'rota', (401, 403, 403, 200, 403, 200, 200)),
            # PER-13 (SEC-10): cliente e barbeiro recebem 404 no detalhe de outro usuário,
            # como para um ID inexistente (antes, 403).
            ('usuário', f'/api/v1/users/{self.admin_a.pk}/', {}, 'rota', (401, 404, 404, 200, 404, 404, 200)),
            ('usuário atual', '/api/v1/users/me/', {}, 'acao', (401, 200, 200, 200, 200, 200, 200)),
            ('barbearias', '/api/v1/barbershops/', {}, 'rota', (401, 200, 200, 200, 200, 200, 200)),
            ('barbearia', f'/api/v1/barbershops/{self.shop_a.pk}/', {}, 'rota', (401, 200, 200, 200, 404, 404, 200)),
            ('barbeiros', '/api/v1/barbers/', {}, 'rota', (401, 200, 200, 200, 200, 200, 200)),
            ('barbeiro', f'/api/v1/barbers/{self.barber_a.pk}/', {}, 'rota', (401, 200, 200, 200, 404, 404, 200)),
            ('serviços', '/api/v1/services/', {}, 'rota', (401, 200, 200, 200, 200, 200, 200)),
            ('serviço', f'/api/v1/services/{self.service_a.pk}/', {}, 'rota', (401, 200, 200, 200, 404, 404, 200)),
            ('agendamentos', '/api/v1/appointments/', {}, 'rota', (401, 200, 200, 200, 200, 200, 200)),
            ('agendamento', f'/api/v1/appointments/{self.appointment_a.pk}/', {}, 'rota', (401, 200, 200, 200, 404, 404, 200)),
            ('horários livres', '/api/v1/appointments/available-slots/',
             {'barbeiro': self.barber_a.pk, 'servico': self.service_a.pk, 'data': dia}, 'acao',
             (401, 200, 200, 200, 403, 404, 403)),
            ('faturamento', '/api/v1/appointments/revenue-report/', {}, 'acao', (401, 403, 403, 200, 403, 200, 403)),
            ('cadastro público', '/api/v1/auth/register/', {}, None, (405,) * 7),
            ('login', '/api/v1/auth/login/', {}, None, (405,) * 7),
            ('renovação do token', '/api/v1/auth/refresh/', {}, None, (405,) * 7),
            ('logout', '/api/v1/auth/logout/', {}, None, (401, 405, 405, 405, 405, 405, 405)),
            ('troca de senha', '/api/v1/auth/password/change/', {}, None, (401, 405, 405, 405, 405, 405, 405)),
            ('recuperação de senha', '/api/v1/auth/password/reset/', {}, None, (405,) * 7),
            ('confirmação da recuperação', '/api/v1/auth/password/reset/confirm/', {}, None, (405,) * 7),
        )

    def pedir(self, papel, caminho, consulta, accept, formato, sufixo, metodo='get'):
        consulta = dict(consulta)
        if formato:
            consulta['format'] = formato
        if sufixo:
            caminho = com_sufixo(caminho, sufixo)
        cabecalhos = {}
        if accept is not None:
            cabecalhos['HTTP_ACCEPT'] = accept
        if papel != 'anonimo':
            cabecalhos['HTTP_AUTHORIZATION'] = f'Bearer {self.tokens[papel]}'
        # Os endpoints de autenticação têm limite de taxa próprio, que não é o
        # assunto destes testes; cada pedido parte de um contador zerado.
        cache.clear()
        return getattr(APIClient(), metodo)(caminho, consulta, **cabecalhos)

    @staticmethod
    def corpo(resposta):
        return resposta.content.decode('utf-8')


class ApiNavegavelDesativadaTests(Ten01Cenario):
    """Nenhum pedido de HTML recebe a API navegável nem qualquer dado."""

    def conferir_html_sem_dados(self):
        for nome, caminho, consulta, sufixos, _status_json in self.rotas():
            for variante, (accept, formato, sufixo, status_esperado) in VARIANTES_HTML.items():
                if sufixo and sufixos is None:
                    continue
                for papel in PAPEIS:
                    with self.subTest(rota=nome, variante=variante, papel=papel, debug=settings.DEBUG):
                        resposta = self.pedir(papel, caminho, consulta, accept, formato, sufixo)
                        corpo = self.corpo(resposta)
                        self.assertNotIn('text/html', resposta.get('Content-Type', ''))
                        self.assertTrue(resposta['Content-Type'].startswith('application/json'))
                        self.assertNotIn('<', corpo, 'a resposta contém marcação HTML')
                        self.assertEqual(resposta.status_code, status_esperado)
                        # O corpo é só a mensagem de erro do DRF, sem registro algum.
                        self.assertEqual(list(json.loads(corpo)), ['detail'])
                        vazados = [marca for marca in TODAS_AS_MARCAS if marca in corpo]
                        self.assertEqual(vazados, [])

    @override_settings(DEBUG=False)
    def test_pedidos_de_html_nao_recebem_html_nem_dados(self):
        self.assertFalse(settings.DEBUG)
        self.conferir_html_sem_dados()

    @override_settings(DEBUG=True)
    def test_pedidos_de_html_nao_recebem_html_nem_dados_com_debug(self):
        self.assertTrue(settings.DEBUG)
        # Com DEBUG=True o Django imprime cada resposta 4xx no console; o
        # assertLogs só recolhe essas linhas.
        with self.assertLogs('django.request', level='WARNING'):
            self.conferir_html_sem_dados()

    def test_casos_reproduzidos_na_auditoria(self):
        """MT-HT-01 a 05, 07, 08 e 12, um a um, como descritos na matriz."""
        casos = (
            ('MT-HT-01', 'cliente_a', '/api/v1/appointments/', 'Accept: text/html'),
            ('MT-HT-02', 'barbeiro_a', '/api/v1/appointments/', 'Accept: text/html'),
            ('MT-HT-03', 'admin_a', '/api/v1/appointments/', 'Accept: text/html'),
            ('MT-HT-04', 'admin_a', f'/api/v1/appointments/{self.appointment_a.pk}/', 'Accept: text/html'),
            ('MT-HT-05', 'admin_a', '/api/v1/barbers/', 'Accept: text/html'),
            ('MT-HT-07', 'sem_barbearia', '/api/v1/appointments/', 'Accept: text/html'),
            ('MT-HT-08', 'admin_c', '/api/v1/barbers/', 'Accept: text/html'),
            ('MT-HT-12', 'cliente_a', '/api/v1/appointments/', '?format=api'),
        )
        for caso, papel, caminho, variante in casos:
            accept, formato, sufixo, status_esperado = VARIANTES_HTML[variante]
            with self.subTest(caso=caso):
                resposta = self.pedir(papel, caminho, {}, accept, formato, sufixo)
                corpo = self.corpo(resposta)
                self.assertEqual(resposta.status_code, status_esperado)
                self.assertNotIn('<select', corpo)
                self.assertNotIn('<option', corpo)
                self.assertEqual([m for m in TODAS_AS_MARCAS if m in corpo], [])

    def test_options_continua_em_json_e_so_anuncia_json(self):
        for papel in PAPEIS[1:]:
            with self.subTest(papel=papel):
                resposta = self.pedir(papel, '/api/v1/appointments/', {}, ACCEPT_AXIOS, None, None, metodo='options')
                corpo = self.corpo(resposta)
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta['Content-Type'].startswith('application/json'))
                self.assertEqual(resposta.json()['renders'], ['application/json'])
                self.assertEqual([m for m in TODAS_AS_MARCAS if m in corpo], [])

    def test_nenhuma_view_registrada_reativa_renderizador_html(self):
        self.assertEqual(api_settings.DEFAULT_RENDERER_CLASSES, [JSONRenderer])

        views = []

        def percorrer(padroes):
            for padrao in padroes:
                if isinstance(padrao, URLResolver):
                    percorrer(padrao.url_patterns)
                elif isinstance(padrao, URLPattern):
                    classe = getattr(padrao.callback, 'cls', None)
                    if classe is not None and hasattr(classe, 'renderer_classes'):
                        # @action(renderer_classes=...) chega pelos initkwargs.
                        initkwargs = getattr(padrao.callback, 'initkwargs', None) or {}
                        renderers = initkwargs.get('renderer_classes', classe.renderer_classes)
                        views.append((str(padrao.pattern), classe.__name__, list(renderers)))

        percorrer(get_resolver().url_patterns)
        # Todas as rotas da API: 7 de autenticação e as dos 5 ViewSets e da
        # raiz, com e sem sufixo de formato.
        self.assertGreaterEqual(len(views), 30)
        for rota, classe, renderers in views:
            with self.subTest(rota=rota, view=classe):
                self.assertEqual(renderers, [JSONRenderer])


class ApiJsonPreservadaTests(Ten01Cenario):
    """O JSON, a autenticação e as permissões continuam como antes da contenção."""

    def test_json_mantem_status_e_isolamento_de_cada_papel(self):
        for nome, caminho, consulta, sufixos, status_json in self.rotas():
            for variante, (accept, formato, sufixo) in VARIANTES_JSON.items():
                if sufixo and sufixos != 'rota':
                    continue
                for papel, status_esperado in zip(PAPEIS, status_json):
                    with self.subTest(rota=nome, variante=variante, papel=papel):
                        resposta = self.pedir(papel, caminho, consulta, accept, formato, sufixo)
                        corpo = self.corpo(resposta)
                        self.assertEqual(resposta.status_code, status_esperado)
                        self.assertTrue(resposta['Content-Type'].startswith('application/json'))
                        json.loads(corpo)
                        grupo = GRUPO_DO_PAPEL[papel]
                        if grupo == 'PLATAFORMA':
                            continue
                        alheias = [
                            marca for outro, marcas in MARCAS.items() if outro != grupo
                            for marca in marcas if marca in corpo
                        ]
                        self.assertEqual(alheias, [])

    def test_listas_json_trazem_os_dados_do_proprio_tenant(self):
        """Garante que a conferência acima não passa por respostas vazias."""
        resposta = self.pedir('admin_a', '/api/v1/appointments/', {}, ACCEPT_AXIOS, None, None)
        self.assertEqual([item['id'] for item in resposta.json()['results']], [self.appointment_a.pk])
        resposta = self.pedir('admin_a', '/api/v1/users/', {}, ACCEPT_AXIOS, None, None)
        self.assertEqual(
            sorted(item['email'] for item in resposta.json()['results']),
            ['alice@alfa.test', 'amanda@alfa.test', 'arthur@alfa.test'],
        )
        resposta = self.pedir('admin_c', '/api/v1/users/', {}, ACCEPT_AXIOS, None, None)
        self.assertEqual([item['email'] for item in resposta.json()['results']], ['gabriela@gama.test'])
        resposta = self.pedir('superusuario', '/api/v1/barbershops/', {}, ACCEPT_AXIOS, None, None)
        self.assertEqual(resposta.json()['count'], 3)

    def test_fluxo_do_frontend_com_axios_continua_funcionando(self):
        """Pedidos como os de frontend/src/api/client.ts: JSON, Bearer e cookie de refresh."""
        frontend = APIClient()
        axios = {'HTTP_ACCEPT': ACCEPT_AXIOS}

        cache.clear()
        login = frontend.post(
            '/api/v1/auth/login/', {'email': 'amanda@alfa.test', 'password': SENHA}, format='json', **axios,
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login['Content-Type'].startswith('application/json'))
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, login.cookies)
        bearer = {'HTTP_AUTHORIZATION': f'Bearer {login.json()["access"]}', **axios}

        me = frontend.get('/api/v1/users/me/', **bearer)
        self.assertEqual((me.status_code, me.json()['email']), (200, 'amanda@alfa.test'))

        cache.clear()
        renovado = frontend.post('/api/v1/auth/refresh/', {}, format='json', **axios)
        self.assertEqual(renovado.status_code, 200)
        self.assertIn('access', renovado.json())
        bearer['HTTP_AUTHORIZATION'] = f'Bearer {renovado.json()["access"]}'

        dia = self.inicio.date().isoformat()
        livres = frontend.get(
            '/api/v1/appointments/available-slots/',
            {'barbeiro': self.barber_a.pk, 'servico': self.service_a.pk, 'data': dia}, **bearer,
        )
        self.assertEqual(livres.status_code, 200)
        self.assertNotIn('10:00', livres.json())

        horario = (self.inicio + timedelta(hours=2)).isoformat()
        criado = frontend.post(
            '/api/v1/appointments/',
            {'cliente': self.cliente_a.pk, 'barbeiro': self.barber_a.pk, 'servico': self.service_a.pk, 'data_hora': horario},
            format='json', **bearer,
        )
        self.assertEqual(criado.status_code, 201, criado.content)
        self.assertTrue(criado['Content-Type'].startswith('application/json'))

        invalido = frontend.post('/api/v1/appointments/', {}, format='json', **bearer)
        self.assertEqual(invalido.status_code, 400)
        self.assertIsInstance(invalido.json(), dict)

        cancelado = frontend.delete(f'/api/v1/appointments/{criado.json()["id"]}/', **bearer)
        self.assertIn(cancelado.status_code, (200, 204))
        self.assertEqual(Appointment.objects.get(pk=criado.json()['id']).status, Appointment.Status.CANCELADO)

        cache.clear()
        saiu = frontend.post('/api/v1/auth/logout/', {}, format='json', **bearer)
        self.assertEqual(saiu.status_code, 204)

    def test_escritas_do_admin_e_do_barbeiro_continuam_em_json(self):
        admin = {'HTTP_AUTHORIZATION': f'Bearer {self.tokens["admin_a"]}', 'HTTP_ACCEPT': ACCEPT_AXIOS}
        resposta = APIClient().patch(
            f'/api/v1/services/{self.service_a.pk}/', {'preco': '55.00'}, format='json', **admin,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['preco'], '55.00')

        barbeiro = {'HTTP_AUTHORIZATION': f'Bearer {self.tokens["barbeiro_a"]}', 'HTTP_ACCEPT': ACCEPT_AXIOS}
        resposta = APIClient().patch(
            f'/api/v1/appointments/{self.appointment_a.pk}/', {'status': 'confirmado'}, format='json', **barbeiro,
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual(resposta.json()['status'], 'confirmado')

        resposta = self.pedir('admin_a', '/api/v1/appointments/revenue-report/', {}, ACCEPT_AXIOS, None, None)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('total_revenue', resposta.json())

    def test_token_invalido_continua_recusado(self):
        resposta = APIClient().get(
            '/api/v1/users/me/', HTTP_AUTHORIZATION='Bearer token-invalido', HTTP_ACCEPT=ACCEPT_AXIOS,
        )
        self.assertEqual(resposta.status_code, 401)
        self.assertTrue(resposta['Content-Type'].startswith('application/json'))
