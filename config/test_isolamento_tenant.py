"""
TEN-01, correção estrutural: referências entre registros limitadas ao tenant.

A contenção (config/test_renderers.py) desligou a API navegável, mas a causa
do vazamento continuava no código: os campos relacionais `cliente`, `barbeiro`,
`servico` (agendamentos) e `user` (barbeiros) e os filtros `barbeiro` e
`servico` da listagem de agendamentos usavam querysets de todas as barbearias.
Isso permitia:

- listar registros de outras barbearias em qualquer formulário montado a
  partir desses campos (o vazamento original do TEN-01);
- diferenciar um ID de outra barbearia de um ID inexistente pelo corpo da
  requisição ("não pertence à sua barbearia" x "objeto não existe") e pelos
  filtros (200 x 400), um oráculo de existência (SEC-10);
- ler o registro alheio no banco antes de recusá-lo;
- para a conta sem barbearia, chegar à validação de agenda de outra barbearia.

Os testes cobrem os papéis das barbearias A e B nos dois sentidos, a conta do
cadastro público, o onboarding, o superusuário e os fluxos legítimos.
"""
import re
from datetime import time, timedelta
from types import SimpleNamespace

from django.core.cache import cache
from django.db import connection
from django.db.models import F, Q
from django.test.utils import CaptureQueriesContext
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone
from django_filters import ModelChoiceFilter, ModelMultipleChoiceFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from config.tenancy import TenantScopedPrimaryKeyRelatedField
from services.models import Service

SENHA = 'Senha-segura-123'
INEXISTENTE = 999999
APPS = ('accounts', 'appointments', 'barbershops', 'services', 'config')
PAPEIS = ('cliente', 'barbeiro', 'admin')


def corpo_normalizado(resposta):
    """Corpo sem os números, que só ecoam o ID enviado pelo próprio cliente."""
    return re.sub(r'\d+', '<n>', resposta.content.decode('utf-8'))


def leituras_sem_tenant(consultas, objeto):
    """Consultas que buscaram o registro pelo ID sem condição de barbearia no WHERE."""
    tabela = objeto._meta.db_table
    padrao = re.compile(rf'"{tabela}"\."id" (= {objeto.pk}\b|IN \({objeto.pk}\))')
    encontradas = []
    for consulta in consultas:
        partes = consulta['sql'].split(' WHERE ', 1)
        if len(partes) == 2 and padrao.search(partes[1]) and 'barbershop_id' not in partes[1]:
            encontradas.append(consulta['sql'])
    return encontradas


class CenarioIsolamento(APITestCase):
    """Barbearias A (Alfa) e B (Beta), conta sem barbearia e superusuário."""

    @classmethod
    def setUpTestData(cls):
        cls.inicio = (timezone.localtime() + timedelta(days=2)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        cls.t = {'A': cls.criar_tenant('A', 'Alfa'), 'B': cls.criar_tenant('B', 'Beta')}
        cls.sem_barbearia = User.objects.create_user(
            email='sergio@sem.test', nome='Sergio Sem Barbearia', password=SENHA,
        )
        cls.superusuario = User.objects.create_superuser(
            email='operador@plataforma.test', nome='Operador Plataforma', password=SENHA,
        )

    @classmethod
    def criar_tenant(cls, chave, nome):
        dominio = f'{nome.lower()}.test'
        shop = Barbershop.objects.create(
            nome=f'Barbearia {nome}', endereco='Rua dos Testes, 100', telefone='11999999999',
            email=f'contato@{dominio}', horario_abertura=time(8), horario_fechamento=time(18),
        )

        def usuario(papel, rotulo, parte_local=None):
            # AUTH-05: o e-mail de login é só ASCII (accounts.emails). O rótulo
            # pode ter acento no nome, mas a parte local do e-mail não.
            return User.objects.create_user(
                email=f'{(parte_local or rotulo).lower()}@{dominio}', nome=f'{rotulo} {nome}', password=SENHA,
                tipo_perfil=papel, barbershop=shop,
            )

        t = SimpleNamespace(chave=chave, nome=nome, shop=shop)
        t.admin = usuario('admin', 'Admin')
        t.cliente = usuario('cliente', 'Cliente')
        t.cliente2 = usuario('cliente', 'Freguês', parte_local='fregues')
        t.barbeiro = Barber.objects.create(user=usuario('barbeiro', 'Barbeiro'), barbershop=shop)
        t.barbeiro2 = Barber.objects.create(user=usuario('barbeiro', 'Navalheiro'), barbershop=shop)
        # Perfil desativado: a conta volta a ser cliente, como em perform_destroy.
        t.barbeiro_inativo = Barber.objects.create(
            user=usuario('cliente', 'Aposentado'), barbershop=shop, ativo=False,
        )
        t.servico = Service.objects.create(barbershop=shop, nome=f'Corte {nome}', preco='50.00', duracao=30)
        t.servico_inativo = Service.objects.create(
            barbershop=shop, nome=f'Antigo {nome}', preco='40.00', duracao=30, ativo=False,
        )
        t.agendamento = Appointment.objects.create(
            barbershop=shop, cliente=t.cliente, barbeiro=t.barbeiro, servico=t.servico,
            data_hora=cls.inicio, preco_historico=t.servico.preco,
        )
        t.usuarios = {'cliente': t.cliente, 'barbeiro': t.barbeiro.user, 'admin': t.admin}
        return t

    # -- auxiliares ---------------------------------------------------------

    def outro(self, t):
        return self.t['B' if t.chave == 'A' else 'A']

    @staticmethod
    def como(usuario):
        cliente = APIClient()
        if usuario is not None:
            cliente.force_authenticate(usuario)
        return cliente

    def horario(self, horas):
        return (self.inicio + timedelta(hours=horas)).isoformat()

    def payload(self, t, **troca):
        dados = {
            'cliente': t.cliente.pk, 'barbeiro': t.barbeiro.pk, 'servico': t.servico.pk,
            'data_hora': self.horario(4),
        }
        dados.update(troca)
        return dados

    @staticmethod
    def fotografia(t):
        return {
            'barbearia': list(Barbershop.objects.filter(pk=t.shop.pk).values()),
            'usuarios': list(User.objects.filter(barbershop=t.shop).order_by('pk').values(
                'pk', 'nome', 'email', 'tipo_perfil', 'is_active', 'barbershop_id',
            )),
            'barbeiros': list(Barber.objects.filter(barbershop=t.shop).order_by('pk').values()),
            'servicos': list(Service.objects.filter(barbershop=t.shop).order_by('pk').values()),
            'agendamentos': list(Appointment.objects.filter(barbershop=t.shop).order_by('pk').values()),
        }

    @staticmethod
    def associacoes_entre_tenants():
        """Agendamentos ou barbeiros ligados a registros de outra barbearia."""
        agendamentos = Appointment.objects.filter(
            ~Q(barbeiro__barbershop=F('barbershop'))
            | ~Q(servico__barbershop=F('barbershop'))
            | ~Q(cliente__barbershop=F('barbershop'))
        ).count()
        barbeiros = Barber.objects.exclude(user__barbershop=F('barbershop')).count()
        return agendamentos + barbeiros

    def assert_sem_dados_de(self, resposta, t):
        corpo = resposta.content.decode('utf-8').lower()
        self.assertNotIn(t.nome.lower(), corpo, 'a resposta contém dados de outra barbearia')

    def assert_mesma_resposta_de_inexistente(self, alheia, inexistente):
        self.assertEqual(alheia.status_code, inexistente.status_code)
        self.assertEqual(corpo_normalizado(alheia), corpo_normalizado(inexistente))

    def ids_alheios(self, destino, campo):
        """IDs de outra barbearia para cada campo, incluindo registros inativos."""
        return {
            'barbeiro': [destino.barbeiro.pk, destino.barbeiro_inativo.pk],
            'servico': [destino.servico.pk, destino.servico_inativo.pk],
            'cliente': [destino.cliente.pk, destino.cliente2.pk],
        }[campo]

    def objeto(self, campo, pk):
        return {'barbeiro': Barber, 'servico': Service, 'cliente': User, 'user': User}[campo].objects.get(pk=pk)


class EscopoEstruturalTests(CenarioIsolamento):
    """Nenhum campo relacional nem filtro consegue listar outra barbearia."""

    @staticmethod
    def serializers_do_projeto():
        encontrados, pendentes = set(), [serializers.BaseSerializer]
        while pendentes:
            classe = pendentes.pop()
            for sub in classe.__subclasses__():
                pendentes.append(sub)
                if sub.__module__.split('.')[0] in APPS and 'test' not in sub.__module__:
                    encontrados.add(sub)
        return sorted(encontrados, key=lambda c: f'{c.__module__}.{c.__name__}')

    def test_todo_campo_relacional_gravavel_usa_escopo_de_tenant(self):
        gravaveis = []
        for classe in self.serializers_do_projeto():
            for nome, campo in classe(context={'request': None}).fields.items():
                relacional = campo.child_relation if isinstance(campo, ManyRelatedField) else campo
                if isinstance(relacional, RelatedField) and not campo.read_only:
                    gravaveis.append(f'{classe.__name__}.{nome}')
                    with self.subTest(campo=f'{classe.__name__}.{nome}'):
                        self.assertIsInstance(relacional, TenantScopedPrimaryKeyRelatedField)
        # Garante que a varredura não passou vazia.
        self.assertEqual(sorted(gravaveis), [
            'AppointmentSerializer.barbeiro', 'AppointmentSerializer.cliente',
            'AppointmentSerializer.servico', 'BarberSerializer.user',
        ])

    def test_todo_filtro_relacional_de_listagem_usa_escopo_de_tenant(self):
        pedido_a = SimpleNamespace(user=self.t['A'].admin)
        pedido_sem = SimpleNamespace(user=self.sem_barbearia)
        verificados = []

        def percorrer(padroes):
            for padrao in padroes:
                if isinstance(padrao, URLResolver):
                    percorrer(padrao.url_patterns)
                elif isinstance(padrao, URLPattern) and getattr(padrao.callback, 'cls', None):
                    classe = padrao.callback.cls
                    if not (getattr(classe, 'filterset_class', None) or getattr(classe, 'filterset_fields', None)):
                        continue
                    view = classe()
                    filtros = DjangoFilterBackend().get_filterset_class(view, classe.queryset.all())
                    for nome, filtro in filtros.base_filters.items():
                        if not isinstance(filtro, (ModelChoiceFilter, ModelMultipleChoiceFilter)):
                            continue
                        chave = f'{classe.__name__}.{nome}'
                        if chave in verificados:
                            continue
                        verificados.append(chave)
                        with self.subTest(filtro=chave):
                            opcoes = filtro.get_queryset(pedido_a)
                            self.assertTrue(opcoes.exists())
                            self.assertFalse(opcoes.exclude(barbershop=self.t['A'].shop).exists())
                            self.assertFalse(filtro.get_queryset(pedido_sem).exists())

        percorrer(get_resolver().url_patterns)
        self.assertEqual(sorted(verificados), ['AppointmentViewSet.barbeiro', 'AppointmentViewSet.servico'])

    def opcoes(self, usuario, serializer_class, instancia=None):
        pedido = SimpleNamespace(user=usuario)
        serializer = serializer_class(instance=instancia, context={'request': pedido})
        return {
            nome: set(campo.get_queryset().values_list('pk', flat=True))
            for nome, campo in serializer.fields.items()
            if isinstance(campo, RelatedField) and not campo.read_only
        }

    def test_opcoes_dos_campos_so_listam_o_proprio_tenant(self):
        """O que um formulário (como o da API navegável) listaria para cada papel."""
        from appointments.serializers import AppointmentSerializer
        from barbershops.serializers import BarberSerializer

        for chave, t in self.t.items():
            proprios = {
                'cliente': set(User.objects.filter(barbershop=t.shop, tipo_perfil='cliente').values_list('pk', flat=True)),
                'barbeiro': set(Barber.objects.filter(barbershop=t.shop).values_list('pk', flat=True)),
                'servico': set(Service.objects.filter(barbershop=t.shop).values_list('pk', flat=True)),
                'user': set(User.objects.filter(barbershop=t.shop).values_list('pk', flat=True)),
            }
            for papel, usuario in t.usuarios.items():
                with self.subTest(barbearia=chave, papel=papel):
                    opcoes = {**self.opcoes(usuario, AppointmentSerializer), **self.opcoes(usuario, BarberSerializer)}
                    self.assertEqual(opcoes, proprios)

        with self.subTest(papel='sem barbearia'):
            opcoes = {**self.opcoes(self.sem_barbearia, AppointmentSerializer), **self.opcoes(self.sem_barbearia, BarberSerializer)}
            self.assertEqual(opcoes, {'cliente': set(), 'barbeiro': set(), 'servico': set(), 'user': set()})

        with self.subTest(papel='anônimo e sem requisição'):
            self.assertEqual(self.opcoes(None, AppointmentSerializer), {'cliente': set(), 'barbeiro': set(), 'servico': set()})
            sem_pedido = AppointmentSerializer(context={})
            self.assertFalse(sem_pedido.fields['barbeiro'].get_queryset().exists())

        with self.subTest(papel='superusuário editando um agendamento de B'):
            opcoes = self.opcoes(self.superusuario, AppointmentSerializer, self.t['B'].agendamento)
            self.assertEqual(opcoes['barbeiro'], set(Barber.objects.filter(barbershop=self.t['B'].shop).values_list('pk', flat=True)))
            self.assertEqual(opcoes['servico'], set(Service.objects.filter(barbershop=self.t['B'].shop).values_list('pk', flat=True)))

        with self.subTest(papel='superusuário sem barbearia criando'):
            # Operador da plataforma: enxerga todas, e a view continua barrando
            # a criação de recursos de tenant sem contexto.
            opcoes = self.opcoes(self.superusuario, AppointmentSerializer)
            self.assertEqual(opcoes['barbeiro'], set(Barber.objects.values_list('pk', flat=True)))

    def test_opcoes_do_formulario_de_filtros_so_listam_o_proprio_tenant(self):
        from appointments.views import AppointmentViewSet

        filtros = DjangoFilterBackend().get_filterset_class(AppointmentViewSet(), Appointment.objects.all())
        for chave, t in self.t.items():
            for papel, usuario in t.usuarios.items():
                with self.subTest(barbearia=chave, papel=papel):
                    form = filtros(data={}, queryset=Appointment.objects.all(), request=SimpleNamespace(user=usuario)).form
                    self.assertEqual(
                        set(form.fields['barbeiro'].queryset.values_list('pk', flat=True)),
                        set(Barber.objects.filter(barbershop=t.shop).values_list('pk', flat=True)),
                    )
                    self.assertEqual(
                        set(form.fields['servico'].queryset.values_list('pk', flat=True)),
                        set(Service.objects.filter(barbershop=t.shop).values_list('pk', flat=True)),
                    )


class ReferenciasCruzadasTests(CenarioIsolamento):
    """IDs de outra barbearia no corpo: recusados, sem oráculo, sem leitura e sem gravação."""

    def tentar(self, metodo, url, usuario, payload_alheio, payload_inexistente, destino, objeto_alheio):
        antes_destino = self.fotografia(destino)
        total = Appointment.objects.count(), Barber.objects.count()
        with CaptureQueriesContext(connection) as consultas:
            alheia = getattr(self.como(usuario), metodo)(url, payload_alheio, format='json')
        inexistente = getattr(self.como(usuario), metodo)(url, payload_inexistente, format='json')
        self.assertEqual(alheia.status_code, 400, alheia.content)
        self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
        self.assert_sem_dados_de(alheia, destino)
        self.assertEqual(leituras_sem_tenant(consultas.captured_queries, objeto_alheio), [])
        self.assertEqual((Appointment.objects.count(), Barber.objects.count()), total)
        self.assertEqual(self.fotografia(destino), antes_destino)
        self.assertEqual(self.associacoes_entre_tenants(), 0)

    def test_criar_agendamento_com_id_de_outro_tenant(self):
        for chave, origem in self.t.items():
            destino = self.outro(origem)
            for papel, usuario in origem.usuarios.items():
                for campo in ('barbeiro', 'servico', 'cliente'):
                    for pk in self.ids_alheios(destino, campo):
                        with self.subTest(origem=chave, papel=papel, campo=campo, pk=pk):
                            self.tentar(
                                'post', '/api/v1/appointments/', usuario,
                                self.payload(origem, **{campo: pk}), self.payload(origem, **{campo: INEXISTENTE}),
                                destino, self.objeto(campo, pk),
                            )

    def test_editar_agendamento_com_id_de_outro_tenant(self):
        for chave, origem in self.t.items():
            destino = self.outro(origem)
            url = f'/api/v1/appointments/{origem.agendamento.pk}/'
            for papel, usuario in origem.usuarios.items():
                for campo in ('barbeiro', 'servico', 'cliente'):
                    for pk in self.ids_alheios(destino, campo):
                        antes = Appointment.objects.filter(pk=origem.agendamento.pk).values().get()
                        with self.subTest(origem=chave, papel=papel, campo=campo, pk=pk, metodo='PATCH'):
                            self.tentar('patch', url, usuario, {campo: pk}, {campo: INEXISTENTE}, destino, self.objeto(campo, pk))
                        with self.subTest(origem=chave, papel=papel, campo=campo, pk=pk, metodo='PUT'):
                            completo = self.payload(origem, data_hora=origem.agendamento.data_hora.isoformat())
                            self.tentar(
                                'put', url, usuario, {**completo, campo: pk}, {**completo, campo: INEXISTENTE},
                                destino, self.objeto(campo, pk),
                            )
                        self.assertEqual(Appointment.objects.filter(pk=origem.agendamento.pk).values().get(), antes)

    def test_cadastrar_barbeiro_com_usuario_de_outro_tenant_ou_sem_barbearia(self):
        for chave, origem in self.t.items():
            destino = self.outro(origem)
            alheios = {
                'cliente de outra barbearia': destino.cliente,
                'admin de outra barbearia': destino.admin,
                'barbeiro de outra barbearia': destino.barbeiro.user,
                'conta sem barbearia': self.sem_barbearia,
                'superusuário': self.superusuario,
            }
            for rotulo, alvo in alheios.items():
                with self.subTest(origem=chave, alvo=rotulo):
                    papel_antes = User.objects.get(pk=alvo.pk).tipo_perfil
                    self.tentar(
                        'post', '/api/v1/barbers/', origem.admin, {'user': alvo.pk, 'especialidade': 'X'},
                        {'user': INEXISTENTE, 'especialidade': 'X'}, destino, alvo,
                    )
                    self.assertEqual(User.objects.get(pk=alvo.pk).tipo_perfil, papel_antes)
                    self.assertFalse(Barber.objects.filter(user=alvo).exclude(pk__in=[destino.barbeiro.pk]).exists())

    def test_registro_de_outro_tenant_nao_e_lido_do_banco(self):
        """A condição de barbearia faz parte da consulta: o registro alheio nunca é carregado."""
        a, b = self.t['A'], self.t['B']
        casos = [
            (f'POST /appointments/ {campo}', 'post', '/api/v1/appointments/', self.payload(a, **{campo: objeto.pk}), objeto)
            for campo, objeto in (('barbeiro', b.barbeiro), ('servico', b.servico), ('cliente', b.cliente))
        ] + [
            ('POST /barbers/ user', 'post', '/api/v1/barbers/', {'user': b.cliente.pk}, b.cliente),
            ('GET /appointments/?barbeiro', 'get', '/api/v1/appointments/', {'barbeiro': b.barbeiro.pk}, b.barbeiro),
            ('GET /appointments/?servico', 'get', '/api/v1/appointments/', {'servico': b.servico.pk}, b.servico),
        ]
        for rotulo, metodo, url, dados, objeto in casos:
            with self.subTest(caso=rotulo):
                with CaptureQueriesContext(connection) as consultas:
                    if metodo == 'post':
                        self.como(a.admin).post(url, dados, format='json')
                    else:
                        self.como(a.admin).get(url, dados)
                self.assertEqual(leituras_sem_tenant(consultas.captured_queries, objeto), [])

    def test_barbearia_no_corpo_e_ignorada(self):
        for chave, origem in self.t.items():
            destino = self.outro(origem)
            with self.subTest(origem=chave, recurso='agendamento'):
                resposta = self.como(origem.admin).post(
                    '/api/v1/appointments/', self.payload(origem, barbershop=destino.shop.pk), format='json',
                )
                self.assertEqual(resposta.status_code, 201, resposta.content)
                self.assertEqual(Appointment.objects.get(pk=resposta.json()['id']).barbershop_id, origem.shop.pk)
            with self.subTest(origem=chave, recurso='barbeiro'):
                resposta = self.como(origem.admin).post(
                    '/api/v1/barbers/', {'user': origem.cliente2.pk, 'barbershop': destino.shop.pk}, format='json',
                )
                self.assertEqual(resposta.status_code, 201, resposta.content)
                self.assertEqual(Barber.objects.get(pk=resposta.json()['id']).barbershop_id, origem.shop.pk)
        self.assertEqual(self.associacoes_entre_tenants(), 0)


class FiltrosDeAgendamentoTests(CenarioIsolamento):
    """MT-FI-01 (SEC-10): o filtro não distingue ID de outra barbearia de ID inexistente."""

    def test_filtros_sem_oraculo_e_sem_dados_alheios(self):
        papeis = [(f'{chave}:{papel}', usuario, t) for chave, t in self.t.items() for papel, usuario in t.usuarios.items()]
        papeis.append(('sem barbearia', self.sem_barbearia, None))
        for rotulo, usuario, t in papeis:
            alheias = [x for x in self.t.values() if x is not t]
            for filtro, atributos in (('barbeiro', ('barbeiro', 'barbeiro_inativo')), ('servico', ('servico', 'servico_inativo'))):
                inexistente = self.como(usuario).get('/api/v1/appointments/', {filtro: INEXISTENTE})
                for destino in alheias:
                    for atributo in atributos:
                        objeto = getattr(destino, atributo)
                        with self.subTest(papel=rotulo, filtro=filtro, alvo=f'{destino.chave}.{atributo}'):
                            with CaptureQueriesContext(connection) as consultas:
                                alheia = self.como(usuario).get('/api/v1/appointments/', {filtro: objeto.pk})
                            self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
                            self.assert_sem_dados_de(alheia, destino)
                            self.assertEqual(leituras_sem_tenant(consultas.captured_queries, objeto), [])
                if t is not None:
                    with self.subTest(papel=rotulo, filtro=filtro, alvo='próprio'):
                        proprio = getattr(t, atributos[0])
                        resposta = self.como(usuario).get('/api/v1/appointments/', {filtro: proprio.pk})
                        self.assertEqual(resposta.status_code, 200)
                        for item in resposta.json()['results']:
                            self.assertEqual(item[filtro], proprio.pk)
                            self.assertEqual(item['barbershop'], t.shop.pk)

    def test_horarios_livres_e_faturamento_sem_oraculo(self):
        """Consultas por ID que já filtravam pela barbearia continuam sem oráculo."""
        dia = self.inicio.date().isoformat()
        for chave, t in self.t.items():
            destino = self.outro(t)
            for papel, usuario in t.usuarios.items():
                for campo in ('barbeiro', 'servico'):
                    with self.subTest(barbearia=chave, papel=papel, consulta='horários livres', campo=campo):
                        base = {'barbeiro': t.barbeiro.pk, 'servico': t.servico.pk, 'data': dia}
                        alheia = self.como(usuario).get('/api/v1/appointments/available-slots/', {**base, campo: getattr(destino, campo).pk})
                        inexistente = self.como(usuario).get('/api/v1/appointments/available-slots/', {**base, campo: INEXISTENTE})
                        self.assertEqual(alheia.status_code, 404)
                        self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
            with self.subTest(barbearia=chave, consulta='faturamento'):
                alheia = self.como(t.admin).get('/api/v1/appointments/revenue-report/', {'barbeiro': destino.barbeiro.pk})
                inexistente = self.como(t.admin).get('/api/v1/appointments/revenue-report/', {'barbeiro': INEXISTENTE})
                self.assertEqual(alheia.status_code, 200)
                self.assertEqual(alheia.json(), inexistente.json())
                self.assertEqual(alheia.json()['total_appointments'], 0)

    def test_listagem_so_traz_o_proprio_tenant(self):
        for chave, t in self.t.items():
            for papel, usuario in t.usuarios.items():
                with self.subTest(barbearia=chave, papel=papel):
                    resposta = self.como(usuario).get('/api/v1/appointments/')
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual([item['id'] for item in resposta.json()['results']], [t.agendamento.pk])
                    self.assert_sem_dados_de(resposta, self.outro(t))


class FluxosLegitimosTests(CenarioIsolamento):
    """O escopo não pode quebrar o que cada papel já fazia na própria barbearia."""

    def test_cliente_agenda_e_remarca(self):
        for chave, t in self.t.items():
            with self.subTest(barbearia=chave):
                cliente = self.como(t.cliente)
                criado = cliente.post('/api/v1/appointments/', self.payload(t), format='json')
                self.assertEqual(criado.status_code, 201, criado.content)
                self.assertEqual(criado.json()['barbershop'], t.shop.pk)
                self.assertEqual(criado.json()['preco_historico'], '50.00')
                remarcado = cliente.patch(
                    f'/api/v1/appointments/{criado.json()["id"]}/',
                    {'barbeiro': t.barbeiro2.pk, 'servico': t.servico.pk, 'data_hora': self.horario(5)}, format='json',
                )
                self.assertEqual(remarcado.status_code, 200, remarcado.content)
                self.assertEqual(remarcado.json()['barbeiro'], t.barbeiro2.pk)

    def test_barbeiro_e_admin_registram_e_confirmam(self):
        for chave, t in self.t.items():
            with self.subTest(barbearia=chave, papel='barbeiro'):
                resposta = self.como(t.barbeiro.user).post(
                    '/api/v1/appointments/', self.payload(t, cliente=t.cliente2.pk), format='json',
                )
                self.assertEqual(resposta.status_code, 201, resposta.content)
                confirmado = self.como(t.barbeiro.user).patch(
                    f'/api/v1/appointments/{t.agendamento.pk}/', {'status': 'confirmado'}, format='json',
                )
                self.assertEqual(confirmado.status_code, 200, confirmado.content)
            with self.subTest(barbearia=chave, papel='admin'):
                resposta = self.como(t.admin).post(
                    '/api/v1/appointments/',
                    self.payload(t, cliente=t.cliente2.pk, barbeiro=t.barbeiro2.pk, data_hora=self.horario(6)),
                    format='json',
                )
                self.assertEqual(resposta.status_code, 201, resposta.content)
                trocado = self.como(t.admin).patch(
                    f'/api/v1/appointments/{resposta.json()["id"]}/', {'barbeiro': t.barbeiro.pk, 'data_hora': self.horario(7)}, format='json',
                )
                self.assertEqual(trocado.status_code, 200, trocado.content)
        self.assertEqual(self.associacoes_entre_tenants(), 0)

    def test_admin_promove_cliente_da_propria_barbearia(self):
        for chave, t in self.t.items():
            with self.subTest(barbearia=chave):
                resposta = self.como(t.admin).post('/api/v1/barbers/', {'user': t.cliente2.pk}, format='json')
                self.assertEqual(resposta.status_code, 201, resposta.content)
                self.assertEqual(User.objects.get(pk=t.cliente2.pk).tipo_perfil, 'barbeiro')

    def test_mensagens_de_validacao_dentro_do_tenant_continuam_iguais(self):
        t = self.t['A']
        resposta = self.como(t.admin).post('/api/v1/appointments/', self.payload(t, barbeiro=t.barbeiro_inativo.pk), format='json')
        self.assertEqual(resposta.json(), {'barbeiro': ['Este barbeiro está inativo.']})
        resposta = self.como(t.admin).post('/api/v1/appointments/', self.payload(t, servico=t.servico_inativo.pk), format='json')
        self.assertEqual(resposta.json(), {'servico': ['Este serviço está inativo e não pode ser agendado.']})
        resposta = self.como(t.admin).post('/api/v1/barbers/', {'user': t.admin.pk}, format='json')
        self.assertEqual(resposta.json(), {'user': ['Usuários administradores não podem ser convertidos em barbeiros.']})
        resposta = self.como(t.admin).post('/api/v1/barbers/', {'user': t.barbeiro.user.pk}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('user', resposta.json())

    def test_barbeiro_so_gerencia_a_propria_agenda(self):
        t = self.t['A']
        resposta = self.como(t.barbeiro.user).post('/api/v1/appointments/', self.payload(t, barbeiro=t.barbeiro2.pk), format='json')
        self.assertEqual(resposta.json(), {'barbeiro': ['Barbeiros só podem gerenciar a própria agenda.']})


class CadastroPublicoEOnboardingTests(CenarioIsolamento):
    """Conta sem barbearia, onboarding de uma barbearia nova e isolamento dela."""

    def registrar_e_entrar(self, email, nome):
        cache.clear()
        resposta = APIClient().post('/api/v1/auth/register/', {'email': email, 'nome': nome, 'password': SENHA}, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertIsNone(resposta.json()['barbershop'])
        cache.clear()
        login = APIClient().post('/api/v1/auth/login/', {'email': email, 'password': SENHA}, format='json')
        self.assertEqual(login.status_code, 200)
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {login.json()["access"]}')
        return cliente

    def test_conta_do_cadastro_publico_nao_referencia_nenhuma_barbearia(self):
        conta = self.registrar_e_entrar('nova@publico.test', 'Conta Publica')
        b = self.t['B']
        antes = self.fotografia(b)
        # MT-AP-27: com o barbeiro de B, horário ocupado e horário livre davam
        # respostas diferentes e revelavam a agenda de B.
        ocupado = conta.post('/api/v1/appointments/', self.payload(b, data_hora=b.agendamento.data_hora.isoformat()), format='json')
        livre = conta.post('/api/v1/appointments/', self.payload(b, data_hora=self.horario(5)), format='json')
        inexistente = conta.post(
            '/api/v1/appointments/',
            self.payload(b, cliente=INEXISTENTE, barbeiro=INEXISTENTE, servico=INEXISTENTE), format='json',
        )
        for resposta in (ocupado, livre):
            # TEN-02: a conta sem barbearia é recusada antes da validação, com a
            # mesma resposta para qualquer corpo (appointments/test_ten02.py).
            self.assertEqual(resposta.status_code, 403)
            self.assertEqual(resposta.json(), {'detail': 'Usuário sem barbearia vinculada.'})
            self.assert_mesma_resposta_de_inexistente(resposta, inexistente)
            self.assert_sem_dados_de(resposta, b)
        self.assertNotIn('data_hora', ocupado.json())
        self.assertEqual(conta.get('/api/v1/appointments/', {'barbeiro': b.barbeiro.pk}).status_code,
                         conta.get('/api/v1/appointments/', {'barbeiro': INEXISTENTE}).status_code)
        self.assertEqual(conta.get('/api/v1/appointments/').json()['count'], 0)
        self.assertEqual(self.fotografia(b), antes)

    def test_onboarding_cria_barbearia_isolada_e_funcional(self):
        dono = self.registrar_e_entrar('dono@gama.test', 'Dono Gama')
        resposta = dono.post('/api/v1/barbershops/', {
            'nome': 'Barbearia Gama', 'endereco': 'Rua Gama, 3', 'telefone': '11977777777',
            'email': 'contato@gama.test', 'horario_abertura': '08:00', 'horario_fechamento': '18:00',
        }, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.content)
        gama = Barbershop.objects.get(pk=resposta.json()['id'])
        self.assertEqual(User.objects.get(email='dono@gama.test').barbershop, gama)

        servico = dono.post('/api/v1/services/', {'nome': 'Corte Gama', 'preco': '30.00', 'duracao': 30}, format='json')
        self.assertEqual(servico.status_code, 201, servico.content)
        clientes = []
        for email in ('c1@gama.test', 'c2@gama.test'):
            criado = dono.post('/api/v1/users/', {'email': email, 'nome': f'Cliente {email}', 'password': SENHA, 'tipo_perfil': 'cliente'}, format='json')
            self.assertEqual(criado.status_code, 201, criado.content)
            clientes.append(criado.json()['id'])
        barbeiro = dono.post('/api/v1/barbers/', {'user': clientes[0]}, format='json')
        self.assertEqual(barbeiro.status_code, 201, barbeiro.content)
        agendamento = dono.post('/api/v1/appointments/', {
            'cliente': clientes[1], 'barbeiro': barbeiro.json()['id'], 'servico': servico.json()['id'], 'data_hora': self.horario(4),
        }, format='json')
        self.assertEqual(agendamento.status_code, 201, agendamento.content)

        # A barbearia nova não alcança A nem B, nem pelo corpo nem pelos filtros.
        for destino in self.t.values():
            for campo, pk in (('barbeiro', destino.barbeiro.pk), ('servico', destino.servico.pk), ('cliente', destino.cliente.pk)):
                with self.subTest(destino=destino.chave, campo=campo):
                    base = {'cliente': clientes[1], 'barbeiro': barbeiro.json()['id'], 'servico': servico.json()['id'], 'data_hora': self.horario(6)}
                    alheia = dono.post('/api/v1/appointments/', {**base, campo: pk}, format='json')
                    inexistente = dono.post('/api/v1/appointments/', {**base, campo: INEXISTENTE}, format='json')
                    self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
            with self.subTest(destino=destino.chave, campo='user'):
                alheia = dono.post('/api/v1/barbers/', {'user': destino.cliente.pk}, format='json')
                inexistente = dono.post('/api/v1/barbers/', {'user': INEXISTENTE}, format='json')
                self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
            with self.subTest(destino=destino.chave, campo='filtro'):
                alheia = dono.get('/api/v1/appointments/', {'barbeiro': destino.barbeiro.pk})
                inexistente = dono.get('/api/v1/appointments/', {'barbeiro': INEXISTENTE})
                self.assert_mesma_resposta_de_inexistente(alheia, inexistente)
        self.assertEqual(self.associacoes_entre_tenants(), 0)


class SuperusuarioTests(CenarioIsolamento):
    """O operador da plataforma mantém a visão de todas as barbearias."""

    def test_superusuario_le_e_filtra_qualquer_barbearia(self):
        su = self.como(self.superusuario)
        for t in self.t.values():
            with self.subTest(barbearia=t.chave):
                resposta = su.get('/api/v1/appointments/', {'barbeiro': t.barbeiro.pk})
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual([item['id'] for item in resposta.json()['results']], [t.agendamento.pk])

    def test_superusuario_edita_dentro_da_barbearia_do_registro(self):
        su = self.como(self.superusuario)
        a, b = self.t['A'], self.t['B']
        url = f'/api/v1/appointments/{a.agendamento.pk}/'
        resposta = su.patch(url, {'barbeiro': a.barbeiro2.pk}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.content)
        resposta = su.patch(url, {'barbeiro': b.barbeiro.pk}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Appointment.objects.get(pk=a.agendamento.pk).barbeiro_id, a.barbeiro2.pk)
        self.assertEqual(self.associacoes_entre_tenants(), 0)

    def test_superusuario_sem_barbearia_continua_sem_criar_recursos_de_tenant(self):
        su = self.como(self.superusuario)
        a = self.t['A']
        total = Appointment.objects.count(), Barber.objects.count()
        resposta = su.post('/api/v1/barbers/', {'user': a.cliente2.pk}, format='json')
        self.assertEqual(resposta.status_code, 403)
        resposta = su.post('/api/v1/appointments/', self.payload(a), format='json')
        self.assertIn(resposta.status_code, (400, 403))
        self.assertEqual((Appointment.objects.count(), Barber.objects.count()), total)
