"""
AUTH-04/05: popula o banco DESCARTÁVEL a45_lab com contas FICTÍCIAS que imitam os estados que o código atual permite
gravar (variações de caixa pela API, domínio em maiúsculas pelo PATCH) e um caso só possível por shell (espaço nas
pontas). Grava direto pelo ORM (User.save não normaliza), para servir de alvo da consulta de colisões e dos testes de
DDL em transação desfeita. Uso: A45_DB=a45_lab DJANGO_SETTINGS_MODULE=a45_settings python a45_dados_legados.py
"""
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['NAME'] == 'a45_lab' and settings.DATABASES['default']['PORT'] == '55432'
from accounts.models import User  # noqa: E402
from appointments.models import Appointment  # noqa: E402
from barbershops.models import Barber, Barbershop  # noqa: E402
from services.models import Service  # noqa: E402

assert User.objects.count() == 0
a = Barbershop.objects.create(nome='Alfa Lab', endereco='x', telefone='1', email='c@alfa.test', horario_abertura=time(9), horario_fechamento=time(19))
b = Barbershop.objects.create(nome='Beta Lab', endereco='x', telefone='2', email='c@beta.test', horario_abertura=time(9), horario_fechamento=time(19))


def u(email, nome, perfil='cliente', shop=None, ativo=True):
    x = User(email=email, nome=nome, tipo_perfil=perfil, barbershop=shop, is_active=ativo)
    x.set_unusable_password()
    x.save()
    return x


admin_a = u('admin.a@alfa.test', 'Ana Admin A', 'admin', a)
admin_b = u('admin.b@beta.test', 'Beatriz Admin B', 'admin', b)
cliente_b = u('cliente.b@beta.test', 'Clara Cliente B', 'cliente', b)
u('Cliente.B@beta.test', 'Aaron Variante', 'cliente', None)                    # AUTH-04: cadastro público com variação
u('ADMIN.B@beta.test', 'Abel Variante', 'cliente', a, ativo=False)             # variação criada pelo admin A e desativada
barbeiro = u('joao.barbeiro@alfa.test', 'João Barbeiro', 'barbeiro', a)
Barber.objects.create(user=barbeiro, barbershop=a, especialidade='Corte')
u('JOAO.BARBEIRO@ALFA.TEST', 'João Duplicado', 'cliente', b)                  # PATCH grava o domínio em maiúsculas
u('Pessoa.Dois@exemplo.test', 'Pessoa Dois', 'cliente', None)                  # muda, sem colisão
u('novo.3@EXEMPLO.TEST', 'Novo Tres', 'cliente', a)                            # muda, sem colisão (só domínio)
u('espaco@exemplo.test ', 'Espaço Final', 'cliente', None)                     # só por shell/SQL: espaço na ponta
u('espaco@exemplo.test', 'Espaço Normal', 'cliente', None)
u('cliente@ÁLFA.test', 'Domínio Unicode', 'cliente', a)                        # não ASCII no domínio
u('tudo.minusculo@alfa.test', 'Normal', 'cliente', a)
barbeiro_b = u('barbeiro.b@beta.test', 'Bento Barbeiro B', 'barbeiro', b)
perfil_b = Barber.objects.create(user=barbeiro_b, barbershop=b, especialidade='Barba')
corte = Service.objects.create(barbershop=b, nome='Corte', preco='50.00', duracao=30)
for hora in ('13:00', '14:00'):                                                # a conta original tem histórico
    Appointment.objects.create(barbershop=b, cliente=cliente_b, barbeiro=perfil_b, servico=corte,
                               data_hora=f'2026-11-20T{hora}:00Z', status='agendado', preco_historico='50.00')
print('contas fictícias:', User.objects.count())
