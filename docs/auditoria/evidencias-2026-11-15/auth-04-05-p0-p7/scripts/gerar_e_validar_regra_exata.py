"""
P2 — gera a pré-verificação com a REGRA EXATA da accounts.0006 (accounts.emails.forma_canonica) em SQL e prova, no
PostgreSQL 18.3 DESCARTÁVEL (pt_BR.UTF-8, 127.0.0.1:55432, banco validacao_sql), que o SQL classifica cada e-mail
exatamente como o Python, ponto de código por ponto de código. Não toca o banco real.

A regra: str.strip() → só U+0021..U+007E (checado antes de converter) → minúsculas. Em SQL:
  btrim(email, <os pontos de código que str.isspace() reconhece, gerados aqui pelo próprio Python>) ~ '^[!-~]+$',
  e o canônico é lower() desse valor (só ASCII, onde Python e PostgreSQL coincidem; seção 30).

Uso: PYTHONPATH=<cópia do código> venv/bin/python gerar_e_validar_regra_exata.py <saída .sql> <relatório .txt>
"""
import csv
import io
import sys

import psycopg2

from accounts.emails import forma_canonica

SAIDA_SQL, RELATORIO = sys.argv[1], sys.argv[2]
ESPACOS = [c for c in range(0x110000) if chr(c).isspace()]
assert len(ESPACOS) == 29, len(ESPACOS)
LITERAL = "U&'" + ''.join(f'\\{c:04X}' for c in ESPACOS) + "'"
CTE = f"""WITH espacos AS (SELECT {LITERAL}::text AS w),
c AS (SELECT u.id, u.email, btrim(u.email, espacos.w) AS sem_espacos FROM accounts_user u, espacos),
r AS (SELECT id, email, (sem_espacos ~ '^[!-~]+$') AS cabe_na_regra,
             CASE WHEN sem_espacos ~ '^[!-~]+$' THEN lower(sem_espacos) END AS canonico FROM c)"""

SQL = f"""-- P2 — pré-verificação com a REGRA EXATA da accounts.0006 (accounts.emails.forma_canonica). SOMENTE LEITURA.
-- Gerado por gerar_e_validar_regra_exata.py; a equivalência com o Python foi provada antes, no banco descartável.
-- Não mostra e-mails, nomes nem papéis: só contagens e ids.
\\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';

\\echo '== R1. Classificação pela regra exata (esperado: fora_da_regra = 0 e grupos_de_colisao = 0)'
{CTE}
SELECT count(*) AS contas,
       count(*) FILTER (WHERE cabe_na_regra AND canonico = email) AS ja_canonicas,
       count(*) FILTER (WHERE cabe_na_regra AND canonico <> email) AS a_normalizar,
       count(*) FILTER (WHERE NOT cabe_na_regra) AS fora_da_regra,
       (SELECT count(*) FROM (SELECT 1 FROM r WHERE cabe_na_regra GROUP BY canonico HAVING count(*) > 1) g) AS grupos_de_colisao
FROM r;

\\echo '== R2. ids fora da regra (interromperiam a migração)'
{CTE}
SELECT id FROM r WHERE NOT cabe_na_regra ORDER BY id;

\\echo '== R3. ids que a migração normalizaria'
{CTE}
SELECT id FROM r WHERE cabe_na_regra AND canonico <> email ORDER BY id;

\\echo '== R4. grupos de colisão após a normalização (ids)'
{CTE}
SELECT array_agg(id ORDER BY id) AS ids FROM r WHERE cabe_na_regra GROUP BY canonico HAVING count(*) > 1;

ROLLBACK;
"""
open(SAIDA_SQL, 'w').write(SQL)

# ---- prova de equivalência no banco descartável
con = psycopg2.connect(host='127.0.0.1', port=55432, user='smoke', dbname='validacao_sql')
cur = con.cursor()
cur.execute("select current_database(), inet_server_port(), current_setting('server_version'), datctype from pg_database where datname = current_database()")
ambiente = cur.fetchone()
assert ambiente[0] == 'validacao_sql' and ambiente[1] == 55432, ambiente
cur.execute('drop table if exists accounts_user')
cur.execute('create table accounts_user (id bigint primary key, email text not null, py_cabe boolean, py_canonico text)')
casos = ['cliente@exemplo.test', 'Cliente@EXEMPLO.TEST', '', '   ', 'a b@x.test', 'a\tb@x.test', 'x@álfa.test',
         'Kelvin@x.test', 'x@x.test﻿', ' x@x.test　', 'x@xn--lfa-1la.test', 'DUP@x.test', 'dup@x.test']
for c in range(1, 0x110000):
    if 0xD800 <= c <= 0xDFFF:
        continue
    ch = chr(c)
    casos += [f'a{ch}b@x.test', f'{ch}a@x.test', f'a@x.test{ch}']
buf = io.StringIO()
escritor = csv.writer(buf, quoting=csv.QUOTE_ALL)  # campo vazio entre aspas = texto vazio, não NULL
for i, email in enumerate(casos, start=1):
    canonico = forma_canonica(email)
    escritor.writerow([i, email, 't' if canonico is not None else 'f', canonico if canonico is not None else ''])
buf.seek(0)
cur.copy_expert("copy accounts_user (id, email, py_cabe, py_canonico) from stdin with (format csv)", buf)
cur.execute(CTE + """
select count(*) as linhas,
       count(*) filter (where r.cabe_na_regra is distinct from u.py_cabe) as cabe_diverge,
       count(*) filter (where u.py_cabe and r.canonico is distinct from u.py_canonico) as canonico_diverge,
       count(*) filter (where r.cabe_na_regra) as cabem
from r join accounts_user u using (id)""")
linhas, cabe_diverge, canonico_diverge, cabem = cur.fetchone()
con.rollback()  # desfaz a tabela de validação inteira (criada nesta mesma transação)
con.close()
texto = (f'Banco descartável: {ambiente[0]} porta {ambiente[1]} PostgreSQL {ambiente[2]} ctype {ambiente[3]}\n'
         f'Espaços do str.strip() (Python): {len(ESPACOS)} pontos de código: {" ".join(f"U+{c:04X}" for c in ESPACOS)}\n'
         f'Linhas comparadas (todos os pontos de código U+0001..U+10FFFF sem substitutos, em 3 posições, mais casos fixos): {linhas}\n'
         f'Divergências em "cabe na regra": {cabe_diverge}\n'
         f'Divergências no valor canônico: {canonico_diverge}\n'
         f'Linhas que cabem na regra: {cabem}\n'
         f'RESULTADO: {"SQL EQUIVALENTE AO PYTHON" if cabe_diverge == 0 and canonico_diverge == 0 else "DIVERGE — NÃO USAR"}\n')
open(RELATORIO, 'w').write(texto)
print(texto)
sys.exit(0 if cabe_diverge == 0 and canonico_diverge == 0 else 1)
