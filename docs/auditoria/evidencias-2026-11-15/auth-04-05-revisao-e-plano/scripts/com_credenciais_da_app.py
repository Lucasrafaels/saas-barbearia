"""
Plano de implantação da accounts.0006 (seção 32): executa `psql`, `pg_dump` ou `pg_restore --list` com as
credenciais do banco DA APLICAÇÃO (settings/.env), sem nunca imprimi-las.

NÃO FOI EXECUTADO na etapa de planejamento. Ler inteiro antes de usar.

Garantias:
- Recusa se o banco configurado não for `barbershop_db`, local (localhost, 127.0.0.1 ou ::1), na porta 5432.
- As credenciais vão ao processo filho só por variáveis de ambiente (PGUSER, PGPASSWORD…), nunca como argumento,
  para não aparecerem em `ps`.
- `--somente-leitura`: a sessão abre com default_transaction_read_only=on e com limites de tempo
  (statement_timeout=30s, lock_timeout=5s). Use em toda consulta e no pg_dump.
- Só aceita psql, pg_dump e `pg_restore --list`. Restaurar NO BANCO REAL não passa por aqui: isso só acontece no
  procedimento de recuperação, com autorização expressa do dono e comando escrito na hora.

Uso (na raiz do projeto, para o Django achar as settings e o .env):
    venv/bin/python <este arquivo> --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -f <consulta.sql>
    venv/bin/python <este arquivo> --somente-leitura -- pg_dump -Fc --no-password -f <arquivo novo>.dump
"""
import os
import sys

PERMITIDOS = ('psql', 'pg_dump', 'pg_restore')


def main():
    args = sys.argv[1:]
    somente_leitura = bool(args) and args[0] == '--somente-leitura'
    if somente_leitura:
        args = args[1:]
    if not args or args[0] != '--' or len(args) < 2:
        sys.exit('uso: com_credenciais_da_app.py [--somente-leitura] -- <psql|pg_dump|pg_restore --list> [argumentos]')
    comando = args[1:]
    if comando[0] not in PERMITIDOS:
        sys.exit(f'RECUSADO: só {", ".join(PERMITIDOS)}.')
    if comando[0] == 'pg_restore' and '--list' not in comando and '-l' not in comando:
        sys.exit('RECUSADO: pg_restore aqui só com --list. Restaurar no banco real é o procedimento de recuperação.')
    if comando[0] == 'pg_dump' and not somente_leitura:
        sys.exit('RECUSADO: pg_dump só com --somente-leitura.')

    sys.path.insert(0, os.getcwd())
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings

    db = settings.DATABASES['default']
    nome, host, porta = db.get('NAME'), db.get('HOST'), str(db.get('PORT'))
    print(f'banco da aplicação: {nome} em {host}:{porta}', file=sys.stderr)
    if (db.get('ENGINE') != 'django.db.backends.postgresql' or nome != 'barbershop_db' or porta != '5432'
            or host not in ('localhost', '127.0.0.1', '::1')):
        sys.exit('RECUSADO: a configuração não é a do banco real esperado (barbershop_db, local, porta 5432).')

    env = {
        'PATH': '/usr/bin:/bin', 'LANG': os.environ.get('LANG', 'C.UTF-8'),
        'PGHOST': host, 'PGPORT': porta, 'PGDATABASE': nome,
        'PGUSER': db.get('USER') or '', 'PGPASSWORD': db.get('PASSWORD') or '',
        'PGAPPNAME': 'implantacao-accounts-0006', 'PGCONNECT_TIMEOUT': '10',
    }
    if somente_leitura:
        env['PGOPTIONS'] = '-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=5000'
    os.execvpe(comando[0], comando, env)


if __name__ == '__main__':
    main()
