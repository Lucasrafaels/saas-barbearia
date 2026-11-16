"""
SEC-10 — sondagem HTTP de GET /appointments/available-slots/?exclude_appointment_id=…, com o SQL que o servidor
executou para cada pedido (log do PostgreSQL descartável com log_statement = 'all' e marcadores por pedido).

Para cada papel de A e de B (cliente, barbeiro, admin), nos dois sentidos, compara o agendamento de outra barbearia
com um ID inexistente (status, corpo, horários, SQL), confere o próprio agendamento, o parâmetro omitido, valores
malformados e a conta sem barbearia, e tira o md5 de todos os agendamentos antes e depois.

Alvo: API ISOLADA (runserver, 127.0.0.1:8767-8770) sobre o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432).
Não imprime nem grava senhas ou tokens.  Uso: python -I sec10_probe.py <estado_seed.json> <url> <rótulo> <log_pg> <saída.json>
"""
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

import psycopg2

ST = json.load(open(sys.argv[1]))
BASE, ROTULO, LOG_PG, SAIDA = sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4], sys.argv[5]
assert re.fullmatch(r'http://127\.0\.0\.1:87(67|68|69|70)', BASE), BASE
API = BASE + '/api/v1'
CREDS, IDS = ST['creds'], ST['ids']
DB = psycopg2.connect(host='127.0.0.1', port=55432, user='smoke', dbname='iso_db')
DB.autocommit = True
with DB.cursor() as c:
    c.execute("select current_database(), inet_server_port(), current_setting('data_directory'), current_setting('log_statement')")
    alvo = c.fetchone()
assert alvo[0] == 'iso_db' and alvo[1] == 55432 and '/scratchpad/iso/pgdata' in alvo[2] and alvo[3] == 'all', alvo


def q(sql, *args):
    with DB.cursor() as c:
        c.execute(sql, args)
        return c.fetchall()


def q1(sql, *args):
    r = q(sql, *args)
    return r[0][0] if r else None


def http(caminho, token=None):
    h = {'Accept': 'application/json, text/plain, */*'}
    if token:
        h['Authorization'] = 'Bearer ' + token
    try:
        r = urllib.request.urlopen(urllib.request.Request(API + caminho, headers=h), timeout=30)
        return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def login(email, senha):
    req = urllib.request.Request(API + '/auth/login/', data=json.dumps({'email': email, 'password': senha}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=30).read())['access']


def foto_agendamentos():
    return q1("select md5(string_agg(t::text, '|' order by id)) from appointments_appointment t")


PEDIDOS = []


def pedir(rotulo, papel, params, token):
    marca = secrets.token_hex(6)
    q(f"select 'SEC10-INICIO-{marca}'")
    status, corpo = http('/appointments/available-slots/?' + urllib.parse.urlencode(params), token)
    q(f"select 'SEC10-FIM-{marca}'")
    PEDIDOS.append({'caso': rotulo, 'papel': papel, 'params': {k: v for k, v in params.items() if k == 'exclude_appointment_id'},
                    'status': status, 'resposta': corpo[:300], 'marca': marca})
    return PEDIDOS[-1]


SHOP = {'A': IDS['shop_a'], 'B': IDS['shop_b']}
PAPEIS = {
    ('A', 'cliente'): 'cliente1@exemplo.test', ('A', 'barbeiro'): 'joao.barbeiro@exemplo.test', ('A', 'admin'): 'admin.a@exemplo.test',
    ('B', 'cliente'): 'cliente.b@exemplo.test', ('B', 'barbeiro'): 'barbeiro.b@exemplo.test', ('B', 'admin'): 'admin.b@exemplo.test',
}


def proprio(tenant, papel, uid):
    """Um agendamento futuro e reagendável que o papel pode excluir (regras atuais)."""
    filtro = {'cliente': 'a.cliente_id = %s', 'barbeiro': 'b.user_id = %s', 'admin': 'a.barbershop_id = %s'}[papel]
    arg = {'cliente': uid, 'barbeiro': uid, 'admin': SHOP[tenant]}[papel]
    return q(f"""select a.id, a.barbeiro_id, a.servico_id,
                        to_char(a.data_hora at time zone 'America/Sao_Paulo', 'YYYY-MM-DD'),
                        to_char(a.data_hora at time zone 'America/Sao_Paulo', 'HH24:MI')
                   from appointments_appointment a join barbershops_barber b on b.id = a.barbeiro_id
                   join services_service s on s.id = a.servico_id
                  where {filtro} and a.status in ('agendado', 'confirmado') and a.data_hora > now() + interval '1 day'
                    and b.ativo and s.ativo
                    and extract(minute from a.data_hora at time zone 'America/Sao_Paulo') = 0
                  order by a.data_hora limit 1""", arg)[0]


FOTO0 = foto_agendamentos()
for (tenant, papel), email in PAPEIS.items():
    outro = 'B' if tenant == 'A' else 'A'
    token = login(email, CREDS[email])
    uid = q1('select id from accounts_user where email=%s', email)
    ag_id, barbeiro, servico, dia, hora = proprio(tenant, papel, uid)
    alheio = q1("select id from appointments_appointment where barbershop_id=%s and status in ('agendado','confirmado') order by data_hora desc limit 1", SHOP[outro])
    base = {'barbeiro': barbeiro, 'servico': servico, 'data': dia}
    rot = f'{papel} {tenant}'
    sem = pedir('omitido', rot, base, token)
    com = pedir('próprio', rot, {**base, 'exclude_appointment_id': ag_id}, token)
    sem['horario_proprio'] = com['horario_proprio'] = hora
    pedir('outra barbearia', rot, {**base, 'exclude_appointment_id': alheio}, token)
    pedir('inexistente', rot, {**base, 'exclude_appointment_id': 999999}, token)
    for valor in ('abc', '-1', '99999999999999999999', ''):
        pedir(f'malformado {valor!r}', rot, {**base, 'exclude_appointment_id': valor}, token)

# Conta do cadastro público (sem barbearia).
sufixo = secrets.token_hex(3)
email_sem, senha_sem = f'sec10.sem.{sufixo}@exemplo.test', 'S10-' + secrets.token_urlsafe(14)
req = urllib.request.Request(API + '/auth/register/', data=json.dumps({'email': email_sem, 'nome': f'SEC10 {sufixo}', 'password': senha_sem}).encode(),
                             headers={'Content-Type': 'application/json'}, method='POST')
urllib.request.urlopen(req, timeout=30)
tok_sem = login(email_sem, senha_sem)
ag_b = q1("select id from appointments_appointment where barbershop_id=%s order by id limit 1", SHOP['B'])
for rotulo, valor in (('sem barbearia, agendamento de B', ag_b), ('sem barbearia, inexistente', 999999), ('sem barbearia, omitido', None)):
    params = {'barbeiro': IDS['barber_b'], 'servico': IDS['service_b'], 'data': '2030-01-07'}
    if valor is not None:
        params['exclude_appointment_id'] = valor
    pedir(rotulo, 'sem barbearia', params, tok_sem)
FOTO1 = foto_agendamentos()

# SQL de cada pedido, lido do log do PostgreSQL entre os marcadores.
log = open(LOG_PG, encoding='utf-8', errors='replace').read()
for p in PEDIDOS:
    m = re.search(rf"SEC10-INICIO-{p['marca']}'(.*?)select 'SEC10-FIM-{p['marca']}", log, re.S)
    comandos = [x for x in re.findall(r'LOG:\s+statement:\s+(.*)', m.group(1)) if re.match(r'\s*(SELECT|INSERT|UPDATE|DELETE)', x, re.I)] if m else []
    # A análise usa o comando inteiro; só a exibição é abreviada (a lista de colunas vira "…").
    completos = [re.sub(r'SELECT .*? FROM', 'SELECT … FROM', x) for x in comandos if 'set_config' not in x]
    p['sql'] = [x[:400] for x in completos]
    busca = [x for x in completos if re.search(r'"appointments_appointment"\."id" = -?\d+', x)]
    p['busca_do_excluido'] = [x[:1500] for x in busca]
    p['busca_sem_barbearia'] = [x[:1500] for x in busca if '"appointments_appointment"."barbershop_id" =' not in x.split(' WHERE ', 1)[-1]]
    p['_sql_completo'] = completos

normalizar = lambda t: re.sub(r'-?\d+', '<n>', t)
grupos = {}
for p in PEDIDOS:
    grupos.setdefault(p['papel'], {})[p['caso']] = p
comparacoes = []
for papel, casos in grupos.items():
    if 'outra barbearia' not in casos:
        continue
    a, i = casos['outra barbearia'], casos['inexistente']
    comparacoes.append({
        'papel': papel,
        'mesmo_status': a['status'] == i['status'], 'mesmo_corpo': a['resposta'] == i['resposta'],
        'status': [a['status'], i['status']], 'resposta_outra_barbearia': a['resposta'], 'resposta_inexistente': i['resposta'],
        'mesmo_sql': [normalizar(x) for x in a['_sql_completo']] == [normalizar(x) for x in i['_sql_completo']],
        'busca_sem_barbearia (outra barbearia)': len(a['busca_sem_barbearia']),
        'joins_na_busca': sum('JOIN' in x for x in a['busca_do_excluido']),
        'malformados_iguais_ao_inexistente': all(casos[k]['status'] == i['status'] and casos[k]['resposta'] == i['resposta']
                                                 for k in casos if k.startswith('malformado') and k != "malformado ''"),
        'vazio_igual_ao_omitido': casos["malformado ''"]['resposta'] == casos['omitido']['resposta'],
        'proprio_libera_o_horario': casos['próprio']['status'] == 200 and f'"{casos["próprio"]["horario_proprio"]}"' in casos['próprio']['resposta']
                                    and f'"{casos["omitido"]["horario_proprio"]}"' not in casos['omitido']['resposta'],
    })
sem = [p for p in PEDIDOS if p['papel'] == 'sem barbearia']
resumo = {
    'comparacoes_outra_barbearia_x_inexistente': len(comparacoes),
    'diferencas_de_status': sum(not c['mesmo_status'] for c in comparacoes),
    'diferencas_de_corpo': sum(not c['mesmo_corpo'] for c in comparacoes),
    'diferencas_de_sql': sum(not c['mesmo_sql'] for c in comparacoes),
    'buscas_do_agendamento_alheio_sem_condicao_de_barbearia': sum(c['busca_sem_barbearia (outra barbearia)'] for c in comparacoes),
    'buscas_com_join': sum(c['joins_na_busca'] for c in comparacoes),
    'malformados_iguais_ao_inexistente': all(c['malformados_iguais_ao_inexistente'] for c in comparacoes),
    'vazio_igual_ao_omitido': all(c['vazio_igual_ao_omitido'] for c in comparacoes),
    'proprio_libera_o_horario': all(c['proprio_libera_o_horario'] for c in comparacoes),
    'sem_barbearia': sorted({(p['status'], p['resposta']) for p in sem}),
    'sem_barbearia_consultas_a_agendamentos': sum(1 for p in sem for x in p['sql'] if 'appointments_appointment' in x),
    'respostas_500': sum(p['status'] >= 500 for p in PEDIDOS),
    'agendamentos_inalterados': FOTO0 == FOTO1,
}
for p in PEDIDOS:
    p.pop('_sql_completo', None)
json.dump({'rotulo': ROTULO, 'api': BASE, 'resumo': resumo, 'comparacoes': comparacoes, 'pedidos': PEDIDOS},
          open(SAIDA, 'w'), ensure_ascii=False, indent=1)
print(f'== {ROTULO}: {json.dumps(resumo, ensure_ascii=False)}')
for c in comparacoes:
    print(f"   {c['papel']}: outra barbearia {c['status'][0]} {c['resposta_outra_barbearia'][:70]} | inexistente {c['status'][1]} {c['resposta_inexistente'][:60]}")
