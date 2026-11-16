"""
P11 — verificações internas SOMENTE LEITURA da regra de e-mail sobre os dados reais. A sessão do banco é aberta com
default_transaction_read_only=on (o PostgreSQL recusaria qualquer escrita). Nada é salvo: só consultas e is_valid().
Não imprime e-mails, nomes nem ids: só contagens. Rodar na raiz do projeto.
"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django  # noqa: E402

django.setup()
from django.db import connection  # noqa: E402

from accounts.emails import forma_canonica  # noqa: E402
from accounts.models import User  # noqa: E402
from accounts.serializers import PublicRegistrationSerializer  # noqa: E402

with connection.cursor() as c:
    c.execute("select current_database(), current_setting('default_transaction_read_only')")
    banco, ro = c.fetchone()
print(f'sessão: banco={banco} somente_leitura={ro}')
assert banco == 'barbershop_db' and ro == 'on', 'a sessão precisa ser somente leitura'
contas = list(User.objects.values_list('pk', 'email', 'is_active'))
falhas = 0


def conferir(rotulo, ok, total):
    global falhas
    print(f"{'ok  ' if ok == total else 'FALHA'} {rotulo}: {ok}/{total}")
    falhas += ok != total


conferir('contas na forma canônica', sum(forma_canonica(e) == e for _, e, _ in contas), len(contas))
conferir('login: a busca do ModelBackend acha a mesma conta com o e-mail em MAIÚSCULAS',
         sum(User.objects.get_by_natural_key(e.upper()).pk == pk for pk, e, _ in contas), len(contas))
conferir('login: idem com caixa trocada e espaços nas pontas',
         sum(User.objects.get_by_natural_key(f'  {e.swapcase()}\t').pk == pk for pk, e, _ in contas), len(contas))
ativas = [(pk, e) for pk, e, a in contas if a]
conferir('recuperação: a busca exata acha a própria conta ativa a partir do e-mail em outra caixa',
         sum(User.objects.filter(email=forma_canonica(e.upper()), is_active=True).values_list('pk', flat=True).first() == pk
             for pk, e in ativas), len(ativas))
inativas = [e for _, e, a in contas if not a]
conferir('recuperação: conta inativa não é encontrada (resposta 204 igual, envio fictício)',
         sum(not User.objects.filter(email=forma_canonica(e.upper()), is_active=True).exists() for e in inativas), len(inativas))


def codigos(email):
    s = PublicRegistrationSerializer(data={'nome': 'Verificação', 'email': email, 'password': 'Navalha-Fict-2026!'})
    s.is_valid()  # só valida; nunca chama save()
    return [d.code for d in s.errors.get('email', [])]


conferir('cadastro (só validação, sem salvar): e-mail existente em MAIÚSCULAS é recusado como duplicado',
         sum(codigos(e.upper()) == ['unique'] for _, e, _ in contas), len(contas))
conferir('cadastro (só validação, sem salvar): e-mails fora da regra são recusados como inválidos',
         sum(codigos(v) == ['invalid'] for v in ['x@álfa.test', 'a b@exemplo.test', 'x@exem​plo.test', 'K@exemplo.test']), 4)
print(f'contas ativas: {len(ativas)} | inativas: {len(inativas)}')
print('RESULTADO INTERNO:', 'OK' if not falhas else f'{falhas} falha(s)')
sys.exit(1 if falhas else 0)
