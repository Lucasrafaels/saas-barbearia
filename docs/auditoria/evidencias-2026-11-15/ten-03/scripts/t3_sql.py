#!/usr/bin/env python3
"""
TEN-03 — junta à saída da sondagem o SQL que o PostgreSQL DESCARTÁVEL registrou entre os marcadores de cada
cenário (log_statement = 'all' só no banco t3_db) e gera a matriz em texto.

Higienização: hashes de senha, tokens JWT, jti e o token de recuperação nunca são copiados.
Uso: python3 -I t3_sql.py <pg.log> <t3_sondagem.json> <saida_com_sql.json> <matriz.md> <estado_seed.json> <sql_por_cenario.txt>
"""
import json
import re
import sys

LOG, ENTRADA, SAIDA, MATRIZ = sys.argv[1:5]
CAB = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ \S+ \[(\d+)\] (\S*) (LOG|ERROR|DETAIL|STATEMENT|HINT|WARNING):  ?(.*)$')
TENANT_DO_ID = {'1': 'A', '2': 'B', 'null': '(sem barbearia)'}


def higienizar(t):
    t = re.sub(r"pbkdf2_sha256\$[^']+", '<hash de senha removido>', t)
    t = re.sub(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', '<token removido>', t)
    t = re.sub(r"'[0-9a-f]{32}'", "'<jti removido>'", t)
    return t


# 1. junta as linhas de continuação de cada entrada do log
entradas = []
for linha in open(LOG, encoding='utf-8', errors='replace'):
    linha = linha.rstrip('\n')
    m = CAB.match(linha)
    if m:
        entradas.append({'pid': m.group(1), 'db': m.group(2), 'tipo': m.group(3), 'texto': m.group(4)})
    elif entradas:
        entradas[-1]['texto'] += '\n' + linha

# 2. separa por cenário
por_cenario, atual = {}, None
for e in entradas:
    mk = re.search(r"T3MARK (\S+) (inicio|fim)", e['texto'])
    if mk:
        atual = mk.group(1) if mk.group(2) == 'inicio' else None
        if atual:
            por_cenario[atual] = []
        continue
    if atual and e['db'] == 't3_db':
        texto = e['texto']
        if e['tipo'] == 'LOG' and texto.startswith('statement: '):
            texto = texto[len('statement: '):]
        por_cenario[atual].append({'tipo': e['tipo'], 'sql': higienizar(texto)})

dados = json.load(open(ENTRADA))
IDS = json.load(open(sys.argv[5]))['ids']
EXIST = re.compile(r'SELECT 1 AS "a" FROM "accounts_user" WHERE (.*?) LIMIT 1', re.S)
for r in dados:
    sql = por_cenario.get(r['id'], [])
    r['sql_do_servidor'] = sql
    consultas = []
    for s in sql:
        m = EXIST.search(s['sql']) if s['tipo'] == 'LOG' else None
        if m and '"accounts_user"."email"' in m.group(1):
            consultas.append({'where': m.group(1), 'filtra_barbearia': 'barbershop_id' in m.group(1)})
    r['consultas_de_existencia_do_email'] = consultas
    r['escritas_em_accounts_user'] = [s['sql'][:160] for s in sql if s['tipo'] == 'LOG' and re.match(r'(INSERT INTO|UPDATE) "accounts_user"', s['sql'])]
    r['erros_do_banco'] = [s['tipo'] + ': ' + s['sql'].split('\n')[0][:200] for s in sql if s['tipo'] in ('ERROR', 'DETAIL')]
    # Que conta tinha o e-mail e se ela está fora do alcance do solicitante (o que ele não poderia listar pela API).
    email_exato = (r['email_sondado'] or '').strip()
    linhas = r['banco_antes']['contas_com_o_email_sem_diferenciar_caixa']
    exatas = [l for l in linhas if l['email'] == email_exato]
    so_caixa = [l for l in linhas if l['email'] != email_exato]
    r['contas_com_o_email_exato_antes'] = exatas
    r['contas_so_com_outra_caixa_antes'] = so_caixa
    papel = r['papel']
    proprio_id = str(IDS.get(papel)) if papel in IDS else None

    def alcancavel(l):
        if papel == 'superuser':
            return True
        if papel == 'admin_a':
            return l['barbershop_id'] == '1'
        return l['id'] == proprio_id

    r['conta_encontrada'] = (', '.join(sorted({TENANT_DO_ID.get(l['barbershop_id'], '?') for l in exatas})) if exatas else
                             ('nenhuma exata; ' + ', '.join(sorted({TENANT_DO_ID.get(l['barbershop_id'], '?') for l in so_caixa})) + ' com outra caixa' if so_caixa else 'nenhuma'))
    r['fora_do_alcance_do_solicitante'] = any(not alcancavel(l) for l in exatas + so_caixa)
    r['consulta_global_sem_filtro'] = bool(consultas) and not any(c['filtra_barbearia'] for c in consultas)
json.dump(dados, open(SAIDA, 'w'), ensure_ascii=False, indent=1)


def resumo_resposta(r):
    if r['resposta_json'] is not None:
        return json.dumps(r['resposta_json'], ensure_ascii=False).replace('|', '\\|')
    if r['status'] == 204:
        return '(sem corpo)'
    return 'HTML "Server Error (500)"' if r['status'] == 500 else r['resposta_integral'][:80]


with open(MATRIZ, 'w') as fh:
    fh.write('# TEN-03 — matriz dos cenários reproduzidos (15/11/2026)\n\n')
    fh.write('API de laboratório com o código atual, sem alteração, `DEBUG=False`, sobre o PostgreSQL 18.3 descartável `t3_db` '
             '(127.0.0.1:55432). Dados fictícios. A barbearia A tem `id=1`; a B, `id=2`.\n\n')
    fh.write('Colunas: **Consulta de existência** = o servidor executou `SELECT 1 AS "a" FROM "accounts_user" WHERE "accounts_user"."email" = … LIMIT 1` '
             '(o `UniqueValidator` do DRF), com ou sem filtro de barbearia. **Conta com o e-mail** = a barbearia da conta que já tinha o e-mail '
             'antes do pedido. **Fora do alcance** = essa conta não poderia ser listada pelo solicitante na API '
             '(admin A lista só A; cliente e barbeiro, só a si; superusuário, todas).\n\n')
    grupo = None
    for r in dados:
        if r['grupo'] != grupo:
            grupo = r['grupo']
            fh.write(f'\n## {grupo}\n\n| ID | Cenário | Papel (tenant) | Pedido | Status | Resposta integral | Criou conta | Alterou alvo | Consulta de existência | Conta com o e-mail | Fora do alcance | ms |\n'
                     '|---|---|---|---|---|---|---|---|---|---|---|---|\n')
        exist = ('sim, sem filtro de barbearia' if r['consulta_global_sem_filtro'] else ('sim, com filtro' if r['consultas_de_existencia_do_email'] else 'não'))
        alt = {None: '—', True: 'sim', False: 'não'}[r['conta_alvo_alterada']]
        fh.write(f"| {r['id']} | {r['descricao']} | {r['papel']} ({r['tenant_do_solicitante']}) | `{r['pedido']}` | {r['status']} | "
                 f"`{resumo_resposta(r)}` | {r['usuarios_criados']} | {alt} | {exist} | {r['conta_encontrada']} | "
                 f"{'**sim**' if r['fora_do_alcance_do_solicitante'] else 'não'} | {r['tempo_ms']} |\n")

with open(sys.argv[6], 'w') as fh:
    fh.write('TEN-03 — SQL registrado pelo PostgreSQL 18.3 DESCARTÁVEL (t3_db) entre os marcadores de cada cenário.\n')
    fh.write("log_statement = 'all' só neste banco. Hashes de senha, tokens e jti removidos. As linhas SELECT de autenticação JWT\n")
    fh.write('(busca do solicitante por id) aparecem antes da validação em todos os pedidos autenticados.\n')
    for r in dados:
        fh.write(f"\n===== {r['id']} | {r['pedido']} | papel={r['papel']} | status={r['status']}\n")
        fh.write(f"cenário: {r['descricao']}\n")
        for q in r['sql_do_servidor']:
            if q['sql'].startswith("SELECT set_config('TimeZone'"):
                continue
            fh.write(f"  [{q['tipo']}] {q['sql']}\n")
print('cenários:', len(dados), '| com SQL:', sum(1 for r in dados if r['sql_do_servidor']))
