"""
PER-13 (SEC-10, terceiro ponto da definição original): `GET /users/{id}/` não pode
revelar se um usuário existe.

Antes, `UserViewSet.get_queryset()` limitava a busca à barbearia, mas não ao que
cada papel pode ver. O registro de outro usuário da mesma barbearia era lido do
banco e só depois recusado por `IsSelfOrAdmin` (403), enquanto um usuário de
outra barbearia ou inexistente recebia 404. Um cliente ou barbeiro descobria,
assim, quais IDs existem na própria barbearia.

Estes testes exigem, na leitura de detalhe (GET e HEAD), a mesma resposta para
todo ID que o solicitante não pode ver e um ID inexistente (status, corpo e
forma do SQL), sem dados do usuário consultado e sem carregar o registro dele.
Também conferem que o acesso legítimo e as demais operações não mudaram.
"""
import re
from datetime import time

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APITestCase

from barbershops.models import Barber, Barbershop

from .models import User

SENHA = 'Senha-segura-123'
INEXISTENTE = 999999
NAO_ENCONTRADO = b'{"detail":"No User matches the given query."}'


def sql_normalizado(consultas):
    return [re.sub(r'\d+', '<n>', c['sql']) for c in consultas]


class CenarioPer13(APITestCase):
    @classmethod
    def setUpTestData(cls):
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
                email=f'{rotulo}@{dominio}', nome=f'{rotulo.capitalize()} {nome}', password=SENHA,
                tipo_perfil=papel, barbershop=shop,
            )

        t = type('Tenant', (), {})()
        t.chave, t.nome, t.shop = nome[0], nome, shop
        t.admin = usuario('admin', 'admin')
        t.admin2 = usuario('admin', 'socio')
        t.cliente = usuario('cliente', 'cliente')
        t.cliente2 = usuario('cliente', 'fregues')
        t.barbeiro = usuario('barbeiro', 'barbeiro')
        t.barbeiro2 = usuario('barbeiro', 'navalheiro')
        for user in (t.barbeiro, t.barbeiro2):
            Barber.objects.create(user=user, barbershop=shop)
        return t

    def setUp(self):
        cache.clear()

    @staticmethod
    def entrar(usuario):
        """Autenticação real (JWT)."""
        cache.clear()
        resposta = APIClient().post('/api/v1/auth/login/', {'email': usuario.email, 'password': SENHA}, format='json')
        assert resposta.status_code == 200, resposta.content
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {resposta.json()["access"]}')
        return api

    def detalhe(self, api, alvo_pk, metodo='get'):
        with CaptureQueriesContext(connection) as consultas:
            resposta = getattr(api, metodo)(f'/api/v1/users/{alvo_pk}/')
        return resposta, consultas.captured_queries

    def assert_sem_dados_do_alvo(self, resposta, alvo):
        corpo = resposta.content.decode().lower()
        self.assertNotIn(alvo.email.lower(), corpo)
        self.assertNotIn(alvo.nome.lower(), corpo)

    def assert_busca_com_escopo(self, consultas, solicitante, alvo_pk):
        """A busca do alvo já traz a barbearia e o próprio solicitante no WHERE: o registro alheio não é carregado."""
        buscas = [c['sql'] for c in consultas if re.search(rf'"accounts_user"\."id" = {alvo_pk}\b', c['sql'])]
        self.assertEqual(len(buscas), 1, buscas)
        onde = buscas[0].split(' WHERE ', 1)[1]
        self.assertIn(f'"accounts_user"."barbershop_id" = {solicitante.barbershop_id}', onde)
        self.assertRegex(onde, rf'"accounts_user"\."id" = {solicitante.pk}\b')


class LeituraDeDetalheTests(CenarioPer13):
    """Casos 1 a 12 e a comparação entre ID não autorizado e inexistente."""

    def nao_autorizados(self, chave, papel):
        t, outro = self.t[chave], self.t['B' if chave == 'A' else 'A']
        mesmos = {
            'cliente': {'outro cliente': t.cliente2, 'barbeiro': t.barbeiro, 'administrador': t.admin},
            'barbeiro': {'outro barbeiro': t.barbeiro2, 'cliente': t.cliente, 'administrador': t.admin},
            'admin': {},
        }[papel]
        alheios = {'cliente de outra barbearia': outro.cliente, 'barbeiro de outra barbearia': outro.barbeiro,
                   'admin de outra barbearia': outro.admin}
        return mesmos, alheios

    def conferir(self):
        for chave, t in self.t.items():
            for papel, eu in (('cliente', t.cliente), ('barbeiro', t.barbeiro), ('admin', t.admin)):
                api = self.entrar(eu)
                inexistente, sql_inexistente = self.detalhe(api, INEXISTENTE)
                self.assertEqual((inexistente.status_code, inexistente.content), (404, NAO_ENCONTRADO))
                mesmos, alheios = self.nao_autorizados(chave, papel)
                for rotulo, alvo in {**mesmos, **alheios}.items():
                    with self.subTest(origem=chave, papel=papel, alvo=rotulo):
                        resposta, consultas = self.detalhe(api, alvo.pk)
                        self.assertEqual((resposta.status_code, resposta.content), (inexistente.status_code, inexistente.content))
                        self.assert_sem_dados_do_alvo(resposta, alvo)
                        self.assertEqual(sql_normalizado(consultas), sql_normalizado(sql_inexistente))
                        if papel != 'admin':
                            self.assert_busca_com_escopo(consultas, eu, alvo.pk)
                        cabeca, _ = self.detalhe(api, alvo.pk, 'head')
                        self.assertEqual(cabeca.status_code, self.detalhe(api, INEXISTENTE, 'head')[0].status_code)

    @override_settings(DEBUG=False)
    def test_nao_autorizado_igual_a_inexistente(self):
        self.conferir()

    @override_settings(DEBUG=True)
    def test_nao_autorizado_igual_a_inexistente_debug(self):
        with self.assertLogs('django.request', level='WARNING'):
            self.conferir()

    def test_cada_um_consulta_a_propria_conta(self):
        for t in self.t.values():
            for eu in (t.cliente, t.barbeiro, t.admin):
                with self.subTest(usuario=eu.email):
                    api = self.entrar(eu)
                    resposta, _ = self.detalhe(api, eu.pk)
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual((resposta.json()['id'], resposta.json()['email']), (eu.pk, eu.email))
                    self.assertEqual(self.detalhe(api, eu.pk, 'head')[0].status_code, 200)

    def test_admin_consulta_usuarios_da_propria_barbearia(self):
        for t in self.t.values():
            api = self.entrar(t.admin)
            for alvo in (t.admin2, t.cliente, t.cliente2, t.barbeiro, t.barbeiro2):
                with self.subTest(barbearia=t.chave, alvo=alvo.email):
                    resposta, _ = self.detalhe(api, alvo.pk)
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual(resposta.json()['email'], alvo.email)

    def test_usuario_sem_barbearia_continua_sem_acesso(self):
        api = self.entrar(self.sem)
        respostas = set()
        for alvo in (self.sem.pk, self.t['A'].cliente.pk, self.t['B'].admin.pk, INEXISTENTE):
            resposta, consultas = self.detalhe(api, alvo)
            respostas.add((resposta.status_code, resposta.content))
            # Só a autenticação lê o banco (a linha do próprio usuário).
            for consulta in consultas:
                self.assertRegex(consulta['sql'].split(' WHERE ', 1)[1], rf'^"accounts_user"\."id" = {self.sem.pk}\b')
        self.assertEqual(respostas, {(404, NAO_ENCONTRADO)})
        # A própria conta continua disponível pelo caminho do frontend.
        self.assertEqual(api.get('/api/v1/users/me/').json()['email'], self.sem.email)

    def test_superusuario_mantem_o_comportamento(self):
        api = self.entrar(self.superusuario)
        for t in self.t.values():
            for alvo in (t.admin, t.cliente, t.barbeiro):
                with self.subTest(alvo=alvo.email):
                    resposta, _ = self.detalhe(api, alvo.pk)
                    self.assertEqual((resposta.status_code, resposta.json()['email']), (200, alvo.email))
        self.assertEqual(self.detalhe(api, INEXISTENTE)[0].content, NAO_ENCONTRADO)


class DemaisOperacoesTests(CenarioPer13):
    """A correção é só da leitura de detalhe: listagem, /users/me/ e escritas mantêm as regras anteriores."""

    def test_listagem_users_sem_regressao(self):
        a = self.t['A']
        resposta = self.entrar(a.admin).get('/api/v1/users/')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            sorted(item['email'] for item in resposta.json()['results']),
            sorted(User.objects.filter(barbershop=a.shop).values_list('email', flat=True)),
        )
        for eu in (a.cliente, a.barbeiro, self.sem):
            with self.subTest(usuario=eu.email):
                self.assertEqual(self.entrar(eu).get('/api/v1/users/').status_code, 403)
        self.assertEqual(self.entrar(self.superusuario).get('/api/v1/users/').json()['count'], User.objects.count())

    def test_users_me_continua(self):
        for eu in (self.t['A'].cliente, self.t['A'].barbeiro, self.t['A'].admin, self.sem, self.superusuario):
            with self.subTest(usuario=eu.email):
                resposta = self.entrar(eu).get('/api/v1/users/me/')
                self.assertEqual((resposta.status_code, resposta.json()['id']), (200, eu.pk))

    def test_escritas_mantem_as_permissoes_anteriores(self):
        a, b = self.t['A'], self.t['B']
        antes = list(User.objects.order_by('pk').values('pk', 'nome', 'is_active', 'tipo_perfil'))
        cliente = self.entrar(a.cliente)
        # Escritas recusadas, como antes (PATCH/PUT em outro usuário da barbearia continuam 403; ver SEC-12).
        self.assertEqual(cliente.patch(f'/api/v1/users/{a.cliente2.pk}/', {'nome': 'X'}, format='json').status_code, 403)
        self.assertEqual(cliente.put(f'/api/v1/users/{a.cliente2.pk}/', {'nome': 'X'}, format='json').status_code, 403)
        self.assertEqual(cliente.patch(f'/api/v1/users/{b.cliente.pk}/', {'nome': 'X'}, format='json').status_code, 404)
        self.assertEqual(cliente.delete(f'/api/v1/users/{a.cliente2.pk}/').status_code, 403)
        self.assertEqual(cliente.post('/api/v1/users/', {'email': 'x@alfa.test', 'nome': 'X', 'password': SENHA}, format='json').status_code, 403)
        self.assertEqual(self.entrar(a.barbeiro).patch(f'/api/v1/users/{a.cliente.pk}/', {'nome': 'X'}, format='json').status_code, 403)
        self.assertEqual(list(User.objects.order_by('pk').values('pk', 'nome', 'is_active', 'tipo_perfil')), antes)
        # Escritas legítimas, como antes.
        self.assertEqual(cliente.patch(f'/api/v1/users/{a.cliente.pk}/', {'nome': 'Cliente Alfa Novo'}, format='json').status_code, 200)
        self.assertEqual(self.entrar(a.barbeiro).patch(f'/api/v1/users/{a.barbeiro.pk}/', {'nome': 'Barbeiro Alfa Novo'}, format='json').status_code, 200)
        admin = self.entrar(a.admin)
        self.assertEqual(admin.patch(f'/api/v1/users/{a.cliente2.pk}/', {'nome': 'Fregues Alfa Novo'}, format='json').status_code, 200)
        self.assertEqual(admin.patch(f'/api/v1/users/{b.cliente.pk}/', {'nome': 'X'}, format='json').status_code, 404)
        criado = admin.post('/api/v1/users/', {'email': 'novo@alfa.test', 'nome': 'Novo Alfa', 'password': SENHA, 'tipo_perfil': 'cliente'}, format='json')
        self.assertEqual(criado.status_code, 201, criado.content)
        self.assertEqual(admin.delete(f'/api/v1/users/{criado.json()["id"]}/').status_code, 204)
        self.assertEqual(User.objects.get(pk=b.cliente.pk).nome, 'Cliente Beta')
