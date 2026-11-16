"""
P8 — etapa C: aplica SÓ a accounts.0006 no BANCO REAL, num único processo que, na MESMA conexão usada pelo migrate,
confere antes: identidade (barbershop_db, 18.3, porta 5432, usuário esperado), sessão de escrita com lock_timeout=5s,
nenhuma outra sessão no banco, nenhuma trava em accounts_user e só a accounts.0006 no plano. Qualquer divergência
interrompe ANTES de migrar. Não imprime credenciais. Rodar na raiz do projeto, com PGOPTIONS definindo lock_timeout.
"""
import io
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402


def parar(motivo):
    print(f'INTERROMPIDO ANTES DE MIGRAR: {motivo}')
    sys.exit(2)


db = settings.DATABASES['default']
if (db['NAME'], db['HOST'], str(db['PORT']), db['USER']) != ('barbershop_db', 'localhost', '5432', 'barbershop_user'):
    parar('configuração do banco diverge')
with connection.cursor() as c:
    c.execute("select current_database(), current_setting('server_version'), inet_server_port(), "
              "current_user = 'barbershop_user', current_setting('transaction_read_only'), current_setting('lock_timeout'), "
              "current_setting('statement_timeout')")
    banco, versao, porta, usuario_ok, somente_leitura, lock_timeout, statement_timeout = c.fetchone()
    print(f'conexão: banco={banco} versão={versao} porta={porta} usuário_confere={usuario_ok} '
          f'transação_somente_leitura={somente_leitura} lock_timeout={lock_timeout} statement_timeout={statement_timeout}')
    if (banco, versao, porta, usuario_ok) != ('barbershop_db', '18.3', 5432, True):
        parar('identidade da conexão diverge')
    if lock_timeout != '5s':
        parar(f'lock_timeout esperado 5s, obtido {lock_timeout}')
    c.execute('select count(*) from pg_stat_activity where datname = current_database() and pid <> pg_backend_pid()')
    outras = c.fetchone()[0]
    c.execute("select count(*) from pg_locks l join pg_class r on r.oid = l.relation "
              "where r.relname = 'accounts_user' and l.pid <> pg_backend_pid()")
    travas = c.fetchone()[0]
    print(f'outras sessões no banco: {outras} | travas de outros em accounts_user: {travas}')
    if outras or travas:
        parar('há outras sessões ou travas')
executor = MigrationExecutor(connection)
plano = executor.migration_plan([('accounts', '0006_email_normalizado')])
print('plano:', [f'{m.app_label}.{m.name}' + (' (reverter)' if volta else '') for m, volta in plano])
if [(m.app_label, m.name, volta) for m, volta in plano] != [('accounts', '0006_email_normalizado', False)]:
    parar('o plano não é exatamente a accounts.0006')
print('--- migrate accounts 0006 (início)')
saida = io.StringIO()
try:
    call_command('migrate', 'accounts', '0006', interactive=False, verbosity=1, stdout=saida, stderr=saida)
except Exception as erro:  # noqa: BLE001
    print(saida.getvalue())
    print(f'ERRO NA MIGRAÇÃO: {type(erro).__name__}: {erro}')
    sys.exit(1)
print(saida.getvalue().rstrip())
print('--- migrate accounts 0006 (fim): concluído sem exceção')
