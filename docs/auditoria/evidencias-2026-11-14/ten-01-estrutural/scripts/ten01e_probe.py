"""
TEN-01 (correção estrutural) — sondagem HTTP de referências entre barbearias.

Para cada papel das barbearias A e B, nos dois sentidos, e para a conta do cadastro público e o admin de
uma barbearia criada no onboarding, envia IDs de outra barbearia nos campos relacionais (corpo de POST,
PATCH e PUT) e nos filtros, e compara cada resposta com a de um ID inexistente. Confere também que nenhuma
referência foi aceita e que nenhuma linha de nenhuma barbearia mudou (md5 de todas as linhas, antes e depois).

Alvo: API ISOLADA (runserver, 127.0.0.1:876x) sobre o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432),
com o seed fictício da auditoria. Não imprime nem grava senhas ou tokens.

Uso: python -I ten01e_probe.py <estado_seed.json> <url_base> <rótulo> <saída.json>
"""
import hashlib
import json
import re
import secrets
import sys
import urllib.error
import urllib.request

import psycopg2

ST = json.load(open(sys.argv[1]))
BASE, ROTULO, SAIDA = sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4]
assert re.fullmatch(r'http://127\.0\.0\.1:87(67|68|69|70)', BASE), BASE
API = BASE + '/api/v1'
CREDS, IDS = ST['creds'], ST['ids']
INEXISTENTE = 999999

DB = psycopg2.connect(host='127.0.0.1', port=55432, user='smoke', dbname='iso_db',
                      options='-c default_transaction_read_only=on')
DB.autocommit = True
with DB.cursor() as c:
    c.execute("select current_database(), inet_server_port(), current_setting('data_directory')")
    alvo = c.fetchone()
assert alvo[0] == 'iso_db' and alvo[1] == 55432 and '/scratchpad/iso/pgdata' in alvo[2], alvo


def q(sql, *args):
    with DB.cursor() as c:
        c.execute(sql, args)
        return c.fetchall()


def q1(sql, *args):
    r = q(sql, *args)
    return r[0][0] if r else None


class Resp:
    def __init__(self, status, body):
        self.status, self.body = status, body


def http(metodo, caminho, token=None, corpo=None):
    h = {'Accept': 'application/json, text/plain, */*'}
    if token:
        h['Authorization'] = 'Bearer ' + token
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode()
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + caminho, data=dados, headers=h, method=metodo)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return Resp(r.status, r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.read().decode('utf-8', 'replace'))


def login(email, senha):
    r = http('POST', '/auth/login/', corpo={'email': email, 'password': senha})
    assert r.status == 200, (email, r.status)
    return json.loads(r.body)['access']


def fotografia():
    """md5 de todas as linhas de tenant, por barbearia (inclui usuários sem barbearia)."""
    tabelas = {
        'barbearias': 'select md5(string_agg(t::text, \'|\' order by id)) from barbershops_barbershop t',
        'usuarios': 'select md5(string_agg(t::text, \'|\' order by id)) from accounts_user t',
        'barbeiros': 'select md5(string_agg(t::text, \'|\' order by id)) from barbershops_barber t',
        'servicos': 'select md5(string_agg(t::text, \'|\' order by id)) from services_service t',
        'agendamentos': 'select md5(string_agg(t::text, \'|\' order by id)) from appointments_appointment t',
    }
    return {k: q1(v) for k, v in tabelas.items()}


def associacoes_entre_tenants():
    return q1("""
        select (select count(*) from appointments_appointment a
                  join barbershops_barber b on b.id = a.barbeiro_id
                  join services_service s on s.id = a.servico_id
                  join accounts_user c on c.id = a.cliente_id
                 where b.barbershop_id <> a.barbershop_id or s.barbershop_id <> a.barbershop_id
                    or c.barbershop_id is distinct from a.barbershop_id)
             + (select count(*) from barbershops_barber b join accounts_user u on u.id = b.user_id
                 where u.barbershop_id is distinct from b.barbershop_id)""")


normalizar = lambda corpo: re.sub(r'\d+', '<n>', corpo)

# ---------------------------------------------------------------------------
# Barbearias, papéis e registros de cada uma (lidos do banco descartável)
# ---------------------------------------------------------------------------
SHOP_A, SHOP_B = IDS['shop_a'], IDS['shop_b']


def registros(shop):
    return {
        'barbeiro': [r[0] for r in q('select id from barbershops_barber where barbershop_id=%s order by id', shop)],
        'servico': [r[0] for r in q('select id from services_service where barbershop_id=%s order by id', shop)],
        'cliente': [r[0] for r in q("select id from accounts_user where barbershop_id=%s and tipo_perfil='cliente' order by id", shop)],
        'usuario': [r[0] for r in q('select id from accounts_user where barbershop_id=%s order by id', shop)],
    }


sufixo = secrets.token_hex(3)
SEM_EMAIL, SEM_PW = f'ten01e.sem.{sufixo}@exemplo.test', 'T01-' + secrets.token_urlsafe(14)
OB_EMAIL, OB_PW = f'ten01e.ob.{sufixo}@exemplo.test', 'T01-' + secrets.token_urlsafe(14)
for email, senha in ((SEM_EMAIL, SEM_PW), (OB_EMAIL, OB_PW)):
    r = http('POST', '/auth/register/', corpo={'email': email, 'nome': f'TEN01E {sufixo}', 'password': senha})
    assert r.status == 201, ('cadastro', r.status)
tok_ob = login(OB_EMAIL, OB_PW)
r = http('POST', '/barbershops/', tok_ob, {'nome': f'TEN01E Barbearia C {sufixo}', 'endereco': 'Rua C', 'telefone': '1',
                                          'email': f'c.{sufixo}@exemplo.test', 'horario_abertura': '09:00', 'horario_fechamento': '18:00'})
assert r.status == 201, ('onboarding', r.status)
SHOP_C = json.loads(r.body)['id']
SUPER_ID = q1('select id from accounts_user where is_superuser order by id limit 1')
SEM_ID = q1('select id from accounts_user where email=%s', SEM_EMAIL)
REG = {SHOP_A: registros(SHOP_A), SHOP_B: registros(SHOP_B)}
NOME = {SHOP_A: 'A', SHOP_B: 'B', SHOP_C: 'C'}
MARCAS = {
    SHOP_A: [n for (n,) in q('select nome from accounts_user where barbershop_id=%s', SHOP_A)] + ['Barbearia Navalha Fictícia'],
    SHOP_B: [n for (n,) in q('select nome from accounts_user where barbershop_id=%s', SHOP_B)] + ['Barbearia Outra Fictícia', 'Corte B'],
}


def proximo_horario(dias, hora):
    return q1("select to_char((current_date + %s) + make_time(%s, 0, 0), 'YYYY-MM-DD\"T\"HH24:MI:SS')", dias, hora)


def papel(email, senha, shop):
    uid = q1('select id from accounts_user where email=%s', email)
    tipo = q1('select tipo_perfil from accounts_user where id=%s', uid)
    barber = q1('select id from barbershops_barber where user_id=%s', uid)
    # Um agendamento futuro e editável que o próprio papel enxerga.
    filtro = {'cliente': 'cliente_id = %s', 'barbeiro': 'barbeiro_id = %s', 'admin': 'barbershop_id = %s'}[tipo]
    arg = {'cliente': uid, 'barbeiro': barber, 'admin': shop}[tipo]
    agend = q1(f"select id from appointments_appointment where {filtro} and status in ('agendado','confirmado') "
               "and data_hora > now() + interval '1 day' order by data_hora limit 1", arg)
    return {'email': email, 'token': login(email, senha), 'tipo': tipo, 'shop': shop, 'uid': uid, 'barber': barber, 'agendamento': agend}


PAPEIS = {
    'cliente A': papel('cliente1@exemplo.test', CREDS['cliente1@exemplo.test'], SHOP_A),
    'barbeiro A': papel('joao.barbeiro@exemplo.test', CREDS['joao.barbeiro@exemplo.test'], SHOP_A),
    'admin A': papel('admin.a@exemplo.test', CREDS['admin.a@exemplo.test'], SHOP_A),
    'cliente B': papel('cliente.b@exemplo.test', CREDS['cliente.b@exemplo.test'], SHOP_B),
    'barbeiro B': papel('barbeiro.b@exemplo.test', CREDS['barbeiro.b@exemplo.test'], SHOP_B),
    'admin B': papel('admin.b@exemplo.test', CREDS['admin.b@exemplo.test'], SHOP_B),
}
SEM = {'token': login(SEM_EMAIL, SEM_PW)}
OB = {'token': login(OB_EMAIL, OB_PW)}

OUT = []


def comparar(rotulo, papel_nome, destino, metodo, caminho, corpo_alheio, corpo_inexistente, token):
    if metodo == 'GET':
        a = http('GET', caminho + corpo_alheio, token)
        i = http('GET', caminho + corpo_inexistente, token)
    else:
        a = http(metodo, caminho, token, corpo_alheio)
        i = http(metodo, caminho, token, corpo_inexistente)
    marcas = [m for m in MARCAS.get(destino, []) if m in a.body]
    OUT.append({
        'caso': rotulo, 'papel': papel_nome, 'destino': NOME.get(destino, destino), 'metodo': metodo, 'caminho': re.sub(r'\d+', '{id}', caminho),
        'status_alheio': a.status, 'status_inexistente': i.status,
        'mesma_resposta': a.status == i.status and normalizar(a.body) == normalizar(i.body),
        'aceito': 200 <= a.status < 300 and metodo != 'GET',
        'resposta_alheia': a.body[:160], 'resposta_inexistente': i.body[:160], 'marcas_alheias': marcas,
    })


FOTO0, ASSOC0 = fotografia(), associacoes_entre_tenants()
for nome, p in PAPEIS.items():
    origem, destino = p['shop'], (SHOP_B if p['shop'] == SHOP_A else SHOP_A)
    ro, rd = REG[origem], REG[destino]
    base = {'cliente': p['uid'] if p['tipo'] == 'cliente' else ro['cliente'][0],
            'barbeiro': p['barber'] if p['tipo'] == 'barbeiro' else ro['barbeiro'][0],
            'servico': ro['servico'][0], 'data_hora': proximo_horario(40, 11)}
    for campo in ('barbeiro', 'servico', 'cliente'):
        for pk in rd[campo]:
            comparar(f'POST /appointments/ {campo}', nome, destino, 'POST', '/appointments/', {**base, campo: pk}, {**base, campo: INEXISTENTE}, p['token'])
            if p['agendamento']:
                url = f'/appointments/{p["agendamento"]}/'
                comparar(f'PATCH /appointments/{{id}}/ {campo}', nome, destino, 'PATCH', url, {campo: pk}, {campo: INEXISTENTE}, p['token'])
                comparar(f'PUT /appointments/{{id}}/ {campo}', nome, destino, 'PUT', url, {**base, campo: pk}, {**base, campo: INEXISTENTE}, p['token'])
    for filtro in ('barbeiro', 'servico'):
        for pk in rd[filtro]:
            comparar(f'GET /appointments/?{filtro}=', nome, destino, 'GET', '/appointments/', f'?{filtro}={pk}', f'?{filtro}={INEXISTENTE}', p['token'])
    if p['tipo'] == 'admin':
        for pk in rd['usuario'] + [SUPER_ID, SEM_ID]:
            comparar('POST /barbers/ user', nome, destino, 'POST', '/barbers/', {'user': pk, 'especialidade': 'X'}, {'user': INEXISTENTE, 'especialidade': 'X'}, p['token'])

# Conta do cadastro público e admin da barbearia C (onboarding) contra A e B.
for nome, p in (('sem barbearia (cadastro público)', SEM), ('admin C (onboarding)', OB)):
    for destino in (SHOP_A, SHOP_B):
        rd = REG[destino]
        base = {'cliente': rd['cliente'][0], 'barbeiro': rd['barbeiro'][0], 'servico': rd['servico'][0], 'data_hora': proximo_horario(40, 11)}
        inexistente = {**base, 'cliente': INEXISTENTE, 'barbeiro': INEXISTENTE, 'servico': INEXISTENTE}
        comparar('POST /appointments/ (todos os campos de outra barbearia)', nome, destino, 'POST', '/appointments/', base, inexistente, p['token'])
        for pk in rd['barbeiro']:
            comparar('GET /appointments/?barbeiro=', nome, destino, 'GET', '/appointments/', f'?barbeiro={pk}', f'?barbeiro={INEXISTENTE}', p['token'])
        if nome.startswith('admin C'):
            for pk in rd['usuario'][:6]:
                comparar('POST /barbers/ user', nome, destino, 'POST', '/barbers/', {'user': pk}, {'user': INEXISTENTE}, p['token'])
    if nome.startswith('sem'):
        # MT-AP-27: horário ocupado x livre do barbeiro de B.
        ocup = q("select barbeiro_id, servico_id, to_char(data_hora at time zone 'America/Sao_Paulo', 'YYYY-MM-DD\"T\"HH24:MI:SS') "
                 "from appointments_appointment where barbershop_id=%s and status in ('agendado','confirmado') and data_hora > now() order by data_hora limit 1", SHOP_B)[0]
        corpo = {'cliente': REG[SHOP_B]['cliente'][0], 'barbeiro': ocup[0], 'servico': ocup[1]}
        comparar('MT-AP-27: POST com horário ocupado x livre de B', nome, SHOP_B, 'POST', '/appointments/',
                 {**corpo, 'data_hora': ocup[2]}, {**corpo, 'data_hora': proximo_horario(45, 15)}, p['token'])

FOTO1, ASSOC1 = fotografia(), associacoes_entre_tenants()
resumo = {
    'pedidos_comparados': len(OUT),
    'oraculos (resposta diferente da de um ID inexistente)': sum(not x['mesma_resposta'] for x in OUT),
    'referencias_aceitas (2xx)': sum(x['aceito'] for x in OUT),
    'respostas_com_nomes_de_outra_barbearia': sum(bool(x['marcas_alheias']) for x in OUT),
    'respostas_500': sum(x['status_alheio'] >= 500 or x['status_inexistente'] >= 500 for x in OUT),
    'banco_inalterado': FOTO0 == FOTO1,
    'tabelas_alteradas': [k for k in FOTO0 if FOTO0[k] != FOTO1[k]],
    'associacoes_entre_tenants (antes, depois)': [ASSOC0, ASSOC1],
}
oraculos = {}
for x in OUT:
    if not x['mesma_resposta']:
        oraculos.setdefault(x['caso'], []).append(x['papel'])
json.dump({'rotulo': ROTULO, 'api': BASE, 'resumo': resumo, 'oraculos_por_caso': oraculos, 'resultados': OUT},
          open(SAIDA, 'w'), ensure_ascii=False, indent=1)
print(f'{ROTULO}: {json.dumps(resumo, ensure_ascii=False)}')
for caso, papeis in oraculos.items():
    print(f'   oráculo: {caso} — {len(papeis)} pedidos ({", ".join(sorted(set(papeis)))})')
