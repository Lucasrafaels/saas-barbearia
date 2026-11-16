"""
TEN-02 — sondagem HTTP com rastreamento SQL pelo próprio PostgreSQL.

Para cada pedido, grava um marcador no log do PostgreSQL antes e depois (o banco descartável iso_db tem
log_statement = 'all'), e depois lê do log os comandos que o servidor executou para aquele pedido.

Casos: conta sem barbearia (horário ocupado e livre de B, barbeiro válido de B, IDs inexistentes, corpo vazio, e
as demais operações), usuário de A contra a agenda de B, agendamento legítimo em A, e cadastro público + onboarding.

Alvo: API ISOLADA (runserver, 127.0.0.1:876x/8773) sobre o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432).
Não imprime nem grava senhas ou tokens.  Uso: python -I ten02_probe.py <estado_seed.json> <url> <rótulo> <log_pg> <saída.json>
"""
import json
import re
import secrets
import sys
import urllib.error
import urllib.request

import psycopg2

ST = json.load(open(sys.argv[1]))
BASE, ROTULO, LOG_PG, SAIDA = sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4], sys.argv[5]
assert re.fullmatch(r'http://127\.0\.0\.1:87(67|68|69|70|73)', BASE), BASE
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


def http(metodo, caminho, token=None, corpo=None):
    h = {'Accept': 'application/json, text/plain, */*'}
    if token:
        h['Authorization'] = 'Bearer ' + token
    dados = json.dumps(corpo).encode() if corpo is not None else None
    if dados:
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + caminho, data=dados, headers=h, method=metodo)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def login(email, senha):
    s, b = http('POST', '/auth/login/', corpo={'email': email, 'password': senha})
    assert s == 200, (email, s)
    return json.loads(b)['access']


CASOS = []


def pedido(grupo, caso, metodo, caminho, token, corpo=None, solicitante=None):
    marca = secrets.token_hex(6)
    q(f"select 'TEN02-INICIO-{marca}'")
    status, corpo_resp = http(metodo, caminho, token, corpo)
    q(f"select 'TEN02-FIM-{marca}'")
    CASOS.append({'grupo': grupo, 'caso': caso, 'metodo': metodo, 'caminho': re.sub(r'\d+', '{id}', caminho.split('?')[0]),
                  'status': status, 'resposta': corpo_resp[:200], 'marca': marca, 'solicitante': solicitante})
    return status, corpo_resp


def horario(dias, hora):
    return q1("select to_char((current_date + %s) + make_time(%s, 0, 0), 'YYYY-MM-DD\"T\"HH24:MI:SS')", dias, hora)


SHOP_A, SHOP_B = IDS['shop_a'], IDS['shop_b']
sufixo = secrets.token_hex(3)
SEM_EMAIL, SEM_PW = f'ten02.sem.{sufixo}@exemplo.test', 'T02-' + secrets.token_urlsafe(14)
s, _ = http('POST', '/auth/register/', corpo={'email': SEM_EMAIL, 'nome': f'TEN02 Sem {sufixo}', 'password': SEM_PW})
assert s == 201, s
SEM_ID = q1('select id from accounts_user where email=%s', SEM_EMAIL)
tok_sem = login(SEM_EMAIL, SEM_PW)

# Agenda de B: um horário ocupado (futuro, não cancelado) do barbeiro de B e um livre do mesmo barbeiro.
ocup = q("select a.id, a.barbeiro_id, a.servico_id, a.cliente_id, "
         "to_char(a.data_hora at time zone 'America/Sao_Paulo', 'YYYY-MM-DD\"T\"HH24:MI:SS') "
         "from appointments_appointment a where a.barbershop_id=%s and a.status in ('agendado','confirmado') "
         "and a.data_hora > now() + interval '1 day' order by a.data_hora limit 1", SHOP_B)[0]
APPT_B, BARB_B, SERV_B, CLI_B, OCUPADO = ocup
LIVRE = horario(47, 15)
base_b = {'cliente': CLI_B, 'barbeiro': BARB_B, 'servico': SERV_B}

G = 'sem barbearia: criação'
pedido(G, '1 horário ocupado de B', 'POST', '/appointments/', tok_sem, {**base_b, 'data_hora': OCUPADO}, SEM_ID)
pedido(G, '2 horário livre de B', 'POST', '/appointments/', tok_sem, {**base_b, 'data_hora': LIVRE}, SEM_ID)
pedido(G, '3 barbeiro válido de B', 'POST', '/appointments/', tok_sem, {'cliente': SEM_ID, 'barbeiro': BARB_B, 'servico': SERV_B, 'data_hora': OCUPADO}, SEM_ID)
pedido(G, '4 IDs inexistentes', 'POST', '/appointments/', tok_sem, {'cliente': 999999, 'barbeiro': 999999, 'servico': 999999, 'data_hora': OCUPADO}, SEM_ID)
pedido(G, 'corpo vazio', 'POST', '/appointments/', tok_sem, {}, SEM_ID)
G = 'sem barbearia: demais operações'
dia_ocupado = OCUPADO[:10]
pedido(G, 'PATCH agendamento de B', 'PATCH', f'/appointments/{APPT_B}/', tok_sem, {'data_hora': LIVRE}, SEM_ID)
pedido(G, 'PATCH inexistente', 'PATCH', '/appointments/999999/', tok_sem, {'data_hora': LIVRE}, SEM_ID)
pedido(G, 'DELETE agendamento de B', 'DELETE', f'/appointments/{APPT_B}/', tok_sem, None, SEM_ID)
pedido(G, 'DELETE inexistente', 'DELETE', '/appointments/999999/', tok_sem, None, SEM_ID)
pedido(G, 'horários livres, dia ocupado de B', 'GET', f'/appointments/available-slots/?barbeiro={BARB_B}&servico={SERV_B}&data={dia_ocupado}', tok_sem, None, SEM_ID)
pedido(G, 'horários livres, dia livre de B', 'GET', f'/appointments/available-slots/?barbeiro={BARB_B}&servico={SERV_B}&data={LIVRE[:10]}', tok_sem, None, SEM_ID)
pedido(G, 'horários livres, IDs inexistentes', 'GET', f'/appointments/available-slots/?barbeiro=999999&servico=999999&data={dia_ocupado}', tok_sem, None, SEM_ID)
pedido(G, 'lista filtrada pelo barbeiro de B', 'GET', f'/appointments/?barbeiro={BARB_B}', tok_sem, None, SEM_ID)
pedido(G, 'lista filtrada por ID inexistente', 'GET', '/appointments/?barbeiro=999999', tok_sem, None, SEM_ID)

# Caso 5: usuários de A contra a agenda de B.
B1 = IDS['barbers'][0]
CORTE = IDS['services'][0]
CLI_A = q1("select id from accounts_user where email='cliente1@exemplo.test'")
for papel, email in (('cliente A', 'cliente1@exemplo.test'), ('admin A', 'admin.a@exemplo.test')):
    tok = login(email, CREDS[email])
    uid = q1('select id from accounts_user where email=%s', email)
    proprio = {'cliente': CLI_A, 'barbeiro': B1, 'servico': CORTE}
    G = f'{papel} contra a agenda de B'
    pedido(G, 'barbeiro de B, horário ocupado', 'POST', '/appointments/', tok, {**proprio, 'barbeiro': BARB_B, 'data_hora': OCUPADO}, uid)
    pedido(G, 'barbeiro de B, horário livre', 'POST', '/appointments/', tok, {**proprio, 'barbeiro': BARB_B, 'data_hora': LIVRE}, uid)
    pedido(G, 'barbeiro inexistente', 'POST', '/appointments/', tok, {**proprio, 'barbeiro': 999999, 'data_hora': OCUPADO}, uid)

# Caso 6: agendamento legítimo em A (horário livre e conflito com a própria agenda).
tok_cli = login('cliente1@exemplo.test', CREDS['cliente1@exemplo.test'])
livre_a = None
for dias in range(50, 70):
    for hora in (9, 10, 11, 14, 15, 16):
        cand = horario(dias, hora)
        if not q1("select count(*) from appointments_appointment where barbeiro_id=%s and status <> 'cancelado' "
                  "and abs(extract(epoch from (data_hora at time zone 'America/Sao_Paulo') - %s::timestamp)) < 3600", B1, cand):
            livre_a = cand
            break
    if livre_a:
        break
G = 'cliente A na própria barbearia'
st, corpo = pedido(G, 'horário livre de A', 'POST', '/appointments/', tok_cli, {'cliente': CLI_A, 'barbeiro': B1, 'servico': CORTE, 'data_hora': livre_a}, CLI_A)
pedido(G, 'mesmo horário de novo (conflito na própria agenda)', 'POST', '/appointments/', tok_cli, {'cliente': CLI_A, 'barbeiro': B1, 'servico': CORTE, 'data_hora': livre_a}, CLI_A)

# Caso 7: cadastro público e onboarding.
OB_EMAIL, OB_PW = f'ten02.ob.{sufixo}@exemplo.test', 'T02-' + secrets.token_urlsafe(14)
G = 'cadastro público e onboarding'
st, _ = http('POST', '/auth/register/', corpo={'email': OB_EMAIL, 'nome': f'TEN02 Dona {sufixo}', 'password': OB_PW})
tok_ob = login(OB_EMAIL, OB_PW)
OB_ID = q1('select id from accounts_user where email=%s', OB_EMAIL)
pedido(G, 'agendar antes do onboarding', 'POST', '/appointments/', tok_ob, {**base_b, 'data_hora': LIVRE}, OB_ID)
st, corpo = pedido(G, 'criar a barbearia', 'POST', '/barbershops/', tok_ob, {'nome': f'TEN02 Barbearia {sufixo}', 'endereco': 'R', 'telefone': '1', 'email': f'c.{sufixo}@exemplo.test', 'horario_abertura': '08:00', 'horario_fechamento': '18:00'}, OB_ID)
st_s, serv = pedido(G, 'criar serviço', 'POST', '/services/', tok_ob, {'nome': 'Corte', 'preco': '30.00', 'duracao': 30}, OB_ID)
clientes = []
for i in (1, 2):
    st_u, u = pedido(G, f'criar cliente {i}', 'POST', '/users/', tok_ob, {'email': f'ten02.c{i}.{sufixo}@exemplo.test', 'nome': f'Cliente {i}', 'password': 'T02-' + secrets.token_urlsafe(12), 'tipo_perfil': 'cliente'}, OB_ID)
    clientes.append(json.loads(u).get('id'))
st_b, barb = pedido(G, 'promover a barbeiro', 'POST', '/barbers/', tok_ob, {'user': clientes[0]}, OB_ID)
pedido(G, 'agendar na barbearia nova', 'POST', '/appointments/', tok_ob, {'cliente': clientes[1], 'barbeiro': json.loads(barb).get('id'), 'servico': json.loads(serv).get('id'), 'data_hora': horario(48, 10)}, OB_ID)

# Leitura do log do PostgreSQL: comandos entre os marcadores de cada pedido.
log = open(LOG_PG, encoding='utf-8', errors='replace').read()
TABELAS_TENANT = ('appointments_appointment', 'barbershops_barber', 'services_service', 'barbershops_barbershop')
for c in CASOS:
    m = re.search(rf"TEN02-INICIO-{c['marca']}'(.*?)select 'TEN02-FIM-{c['marca']}", log, re.S)
    comandos = re.findall(r'LOG:\s+statement:\s+(.*)', m.group(1)) if m else None
    comandos = [x for x in (comandos or []) if re.match(r'\s*(SELECT|INSERT|UPDATE|DELETE)', x, re.I)]
    c['sql'] = [re.sub(r'SELECT .*? FROM', 'SELECT … FROM', x)[:260] for x in comandos]
    c['consultas'] = len(comandos)
    c['agenda_consultada'] = [x[:260] for x in comandos if 'FROM "appointments_appointment"' in x and '"barbeiro_id" =' in x]
    c['leituras_de_tenant'] = sum(any(f'"{t}"' in x for t in TABELAS_TENANT) for x in comandos)
    c['leituras_de_outros_usuarios'] = sum(
        1 for x in comandos if '"accounts_user"' in x and c['solicitante'] and not re.search(rf'"accounts_user"\."id" = {c["solicitante"]}\b', x))

normalizar = lambda t: re.sub(r'\d+', '<n>', t)
resumo = {}
for grupo in dict.fromkeys(c['grupo'] for c in CASOS):
    cs = [c for c in CASOS if c['grupo'] == grupo]
    resumo[grupo] = {
        'pedidos': len(cs),
        'status': sorted({c['status'] for c in cs}),
        'respostas_distintas': len({c['resposta'] for c in cs}),
        'respostas_distintas_sem_numeros': len({normalizar(c['resposta']) for c in cs}),
        'consultas_a_agenda': sum(len(c['agenda_consultada']) for c in cs),
        'leituras_de_tabelas_de_tenant': sum(c['leituras_de_tenant'] for c in cs),
    }
json.dump({'rotulo': ROTULO, 'api': BASE, 'resumo': resumo, 'casos': CASOS}, open(SAIDA, 'w'), ensure_ascii=False, indent=1)
print(f'== {ROTULO}')
for g, r in resumo.items():
    print(f'   {g}: {json.dumps(r, ensure_ascii=False)}')
for c in CASOS:
    if c['grupo'].startswith('sem barbearia: criação') or 'agenda de B' in c['grupo']:
        print(f"      [{c['grupo']} | {c['caso']}] {c['status']} {c['resposta'][:110]} | consultas={c['consultas']} agenda={len(c['agenda_consultada'])}")
