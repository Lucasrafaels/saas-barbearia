"""
Executa, no banco da aplicação, SÓ a identificação ou SÓ a cópia autorizada da consulta de colisões.
As credenciais vêm das settings do Django (.env) e são passadas ao psql por variáveis de ambiente do processo filho:
nunca são impressas. A sessão é aberta como somente leitura (default_transaction_read_only=on), com limites de tempo.
Recusa rodar se o banco, o host ou a porta não forem os esperados.
Uso: python executar_somente_leitura.py identidade|consulta [arquivo.sql]
"""
import os
import subprocess
import sys

sys.path.insert(0, '/home/lucasrafael/arquivos_faculdade/saas_barbearia')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.conf import settings  # noqa: E402

db = settings.DATABASES['default']
nome, host, porta, motor = db.get('NAME'), db.get('HOST'), str(db.get('PORT')), db.get('ENGINE', '')
print(f'configuração da aplicação: motor={motor.rsplit(".", 1)[-1]} banco={nome} host={host} porta={porta}')
if motor != 'django.db.backends.postgresql' or nome != 'barbershop_db' or porta != '5432' or host not in ('localhost', '127.0.0.1', '::1'):
    sys.exit('RECUSADO: a configuração não é a do banco real esperado (barbershop_db, local, porta 5432).')

env = {
    'PATH': '/usr/bin:/bin', 'PGHOST': host, 'PGPORT': porta, 'PGDATABASE': nome,
    'PGUSER': db.get('USER') or '', 'PGPASSWORD': db.get('PASSWORD') or '',
    'PGAPPNAME': 'auditoria-auth04-05-somente-leitura', 'PGCONNECT_TIMEOUT': '10',
    'PGOPTIONS': '-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000 '
                 '-c idle_in_transaction_session_timeout=60000',
}
if sys.argv[1] == 'identidade':
    sql = ("SELECT current_database() AS banco, current_setting('server_version') AS versao, "
           "inet_server_addr() AS endereco, inet_server_port() AS porta, "
           "current_setting('default_transaction_read_only') AS sessao_somente_leitura, "
           "current_setting('statement_timeout') AS limite_por_comando, current_setting('lock_timeout') AS limite_de_trava")
    cmd = ['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-c', sql]
elif sys.argv[1] == 'consulta':
    cmd = ['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-f', sys.argv[2]]
else:
    sys.exit('modo inválido')
r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
sys.stdout.write(r.stderr)
print(f'psql exit={r.returncode}')
