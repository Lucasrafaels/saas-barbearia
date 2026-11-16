"""
Auditoria de isolamento multi-tenant do BarberPro — sondagem HTTP + verificação no banco.

Alvo: API ISOLADA em 127.0.0.1:8767 (mesmo código do projeto) com banco DESCARTÁVEL
PostgreSQL 18.3 em 127.0.0.1:55432 (iso_db), populado com dados fictícios (seed da auditoria).
Nunca aponta para o banco real. Não imprime senhas nem tokens.

Uso: python iso_probe.py <estado_seed.json> <saida.json>
Requer: Python com psycopg2 (venv do projeto). Só biblioteca padrão para HTTP.
"""
import base64
import hashlib
import json
from http.cookiejar import CookieJar
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import psycopg2

ROOT = 'http://127.0.0.1:8767'
API = ROOT + '/api/v1'
assert ':8767' in ROOT

# ---------------------------------------------------------------------------
# Banco descartável (somente para conferência; a sondagem não escreve nele)
# ---------------------------------------------------------------------------
DB = psycopg2.connect(host='127.0.0.1', port=55432, user='smoke', dbname='iso_db')
DB.autocommit = True
with DB.cursor() as c:
    c.execute("select current_database(), inet_server_port(), current_setting('data_directory')")
    DB_ALVO = c.fetchone()
assert DB_ALVO[0] == 'iso_db' and DB_ALVO[1] == 55432 and '/scratchpad/iso/pgdata' in DB_ALVO[2], DB_ALVO


def q(sql, *args):
    with DB.cursor() as c:
        c.execute(sql, args)
        return c.fetchall()


def q1(sql, *args):
    r = q(sql, *args)
    return r[0][0] if r else None


EXCL = {'last_login'}


def row_hash(table, pk):
    with DB.cursor() as c:
        c.execute(f'select * from {table} where id = %s', (pk,))
        row = c.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in c.description]
    data = {k: str(v) for k, v in zip(cols, row) if k not in EXCL}
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def cols(table, pk, *nomes):
    return q(f'select {", ".join(nomes)} from {table} where id = %s', pk)


TENANT_TABLES = {
    'barbershops_barbershop': 'id = %s',
    'accounts_user': 'barbershop_id = %s',
    'barbershops_barber': 'barbershop_id = %s',
    'services_service': 'barbershop_id = %s',
    'appointments_appointment': 'barbershop_id = %s',
}


def tenant_snapshot(shop_id):
    snap = {}
    for table, where in TENANT_TABLES.items():
        with DB.cursor() as c:
            c.execute(f'select * from {table} where {where} order by id', (shop_id,))
            cols = [d[0] for d in c.description]
            rows = [{k: str(v) for k, v in zip(cols, r) if k not in EXCL} for r in c.fetchall()]
        snap[table] = (len(rows), hashlib.md5(json.dumps(rows, sort_keys=True).encode()).hexdigest())
    # tokens de B revogados (logout cruzado)
    snap['token_blacklist_de_usuarios'] = q1(
        'select count(*) from token_blacklist_blacklistedtoken b join token_blacklist_outstandingtoken o '
        'on o.id = b.token_id join accounts_user u on u.id = o.user_id where u.barbershop_id = %s', shop_id)
    return snap


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class Resp:
    def __init__(self, status, body, headers):
        self.status, self.raw, self.headers = status, body, headers
        try:
            self.json = json.loads(body) if body else None
        except Exception:
            self.json = None

    @property
    def text(self):
        return self.raw if isinstance(self.raw, str) else ''


def http(method, url, token=None, body=None, headers=None, raw=None, content_type=None, opener=None):
    h = dict(headers or {})
    data = None
    if token:
        h['Authorization'] = 'Bearer ' + token
    if body is not None:
        data = json.dumps(body).encode()
        h['Content-Type'] = 'application/json'
    if raw is not None:
        data = raw
        h['Content-Type'] = content_type
    h.setdefault('Accept', 'application/json')
    req = urllib.request.Request(url if url.startswith('http') else API + url, data=data, headers=h, method=method)
    op = opener or urllib.request.build_opener(NoRedirect)
    try:
        r = op.open(req, timeout=30)
        return Resp(r.status, r.read().decode('utf-8', 'replace'), dict(r.headers))
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.read().decode('utf-8', 'replace'), dict(e.headers))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


ST = json.load(open(sys.argv[1]))
CREDS, IDS = ST['creds'], ST['ids']


class U:
    """Sessão de um usuário (token em memória, nunca impresso)."""

    def __init__(self, email, password=None):
        self.email = email
        r = http('POST', '/auth/login/', body={'email': email, 'password': password or CREDS[email]})
        assert r.status == 200, (email, r.status)
        self.token = r.json['access']
        sc = r.headers.get('Set-Cookie', '')
        m = re.search(r'barbearia_refresh=([^;]+)', sc)
        self.refresh = m.group(1) if m else None
        self.me = http('GET', '/users/me/', self.token).json

    def __call__(self, method, path, body=None, **kw):
        return http(method, path, self.token, body, **kw)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
OUT = []


def rec(tid, recurso, papel, origem, destino, operacao, esperado, observado, ok, evidencia, sev='—', area=''):
    OUT.append({
        'id': tid, 'area': area, 'recurso': recurso, 'papel': papel, 'origem': origem, 'destino': destino,
        'operacao': operacao, 'esperado': esperado, 'observado': str(observado)[:300], 'ok': bool(ok),
        'evidencia': evidencia, 'severidade': '—' if ok else sev,
    })


DENY = (403, 404)


def denied(r):
    return r.status in DENY


def short(r):
    j = r.json
    if isinstance(j, dict):
        return f'{r.status} {json.dumps(j, ensure_ascii=False)[:140]}'
    return f'{r.status}'


# ---------------------------------------------------------------------------
# Identificadores
# ---------------------------------------------------------------------------
SHOP_A, SHOP_B = IDS['shop_a'], IDS['shop_b']
ADMIN_A, ADMIN_B, CLI_B, SUPER = IDS['admin_a'], IDS['admin_b'], IDS['cliente_b'], IDS['superuser']
B1, B2, B3 = IDS['barbers']
BARBER_B = IDS['barber_b']
BARBER_B_USER = q1('select user_id from barbershops_barber where id = %s', BARBER_B)
CORTE, BARBA, COMBO, PIGM = IDS['services'][:4]
SVC_B = IDS['service_b']
CLIS_A = IDS['clientes']
APPT_B = q1('select min(id) from appointments_appointment where barbershop_id = %s', SHOP_B)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')


def multipart(fields, files):
    bnd = 'iso' + secrets.token_hex(8)
    parts = []
    for k, v in fields.items():
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fname, content, ctype) in files.items():
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + content + b'\r\n')
    parts.append(f'--{bnd}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={bnd}'


def futuro(dias, h, m=0):
    d = date.today() + timedelta(days=dias)
    return f'{d.isoformat()}T{h:02d}:{m:02d}:00-03:00'


# ---------------------------------------------------------------------------
# Sessões
# ---------------------------------------------------------------------------
adminA, barbA, cliA = U('admin.a@exemplo.test'), U('joao.barbeiro@exemplo.test'), U('cliente1@exemplo.test')
adminB, barbB, cliB = U('admin.b@exemplo.test'), U('barbeiro.b@exemplo.test'), U('cliente.b@exemplo.test')
sup = U('plataforma@exemplo.test')
CLI_A1 = cliA.me['id']

# Usuário de cadastro público (sem barbearia). O corpo tenta, sem sucesso esperado, escolher barbearia e papel.
SEM_EMAIL, SEM_PW = 'sem.tenant@exemplo.test', 'Iso-' + secrets.token_urlsafe(14)
r = http('POST', '/auth/register/', body={'email': SEM_EMAIL, 'nome': 'Sem Barbearia Fictício', 'password': SEM_PW,
                                          'barbershop': SHOP_B, 'tipo_perfil': 'admin', 'is_staff': True, 'is_superuser': True})
SEM_ID = (r.json or {}).get('id')
row = q('select barbershop_id, tipo_perfil, is_staff, is_superuser from accounts_user where id = %s', SEM_ID)
rec('MT-AU-01', 'POST /auth/register/', 'anônimo', '—', 'B', 'cadastro público com barbershop=B, tipo_perfil=admin, is_staff, is_superuser no corpo',
    '201; no banco: sem barbearia, cliente, sem staff/superuser', f'{r.status}; banco={row}',
    r.status == 201 and row == [(None, 'cliente', False, False)],
    'POST /api/v1/auth/register/ {email,nome,password,barbershop:<B>,tipo_perfil:"admin",is_staff:true,is_superuser:true}; SELECT barbershop_id,tipo_perfil,is_staff,is_superuser FROM accounts_user', 'P0', 'Autenticação')
sem = U(SEM_EMAIL, SEM_PW)

# ---------------------------------------------------------------------------
# Preparação legítima pela barbearia B (antes da fotografia de B)
# ---------------------------------------------------------------------------
svc_b2 = adminB('POST', '/services/', {'nome': 'Barba B', 'preco': '30.00', 'duracao': 30}).json['id']
svc_b3 = adminB('POST', '/services/', {'nome': 'Inativo B', 'preco': '10.00', 'duracao': 30}).json['id']
adminB('DELETE', f'/services/{svc_b3}/')
appt_b2 = adminB('POST', '/appointments/', {'cliente': CLI_B, 'barbeiro': BARBER_B, 'servico': SVC_B,
                                            'data_hora': futuro(31, 10), 'status': 'confirmado'}).json['id']
raw, ct = multipart({}, {'logo': ('logo-b.png', PNG, 'image/png')})
rl = adminB('PATCH', f'/barbershops/{SHOP_B}/', raw=raw, content_type=ct)
assert rl.status == 200, ('logo B', rl.status, rl.json)
LOGO_B_URL = (rl.json or {}).get('logo')
# Objetos de A usados nos testes de "mover para B"
appt_a = cliA('POST', '/appointments/', {'cliente': CLI_A1, 'barbeiro': B1, 'servico': CORTE, 'data_hora': futuro(32, 10)}).json['id']
appt_a_admin = adminA('POST', '/appointments/', {'cliente': CLIS_A[1], 'barbeiro': B2, 'servico': CORTE, 'data_hora': futuro(32, 11)}).json['id']
appt_a_other_cli = q1('select min(id) from appointments_appointment where barbershop_id=%s and cliente_id=%s', SHOP_A, CLIS_A[1])
appt_a_other_barber = q1('select min(id) from appointments_appointment where barbershop_id=%s and barbeiro_id=%s and status in (%s,%s) and data_hora > now()', SHOP_A, B2, 'agendado', 'confirmado')

MARCAS_B = ['Clara Cliente B', 'Bento Barbeiro B', 'Beatriz Proprietária B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Outra Fictícia']
SNAP_B0 = tenant_snapshot(SHOP_B)
SEM_ROW0 = row_hash('accounts_user', SEM_ID)

# ===========================================================================
# 1. Barbearia (tenant)
# ===========================================================================
A = 'Barbearia e configurações'
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    r = s('GET', '/barbershops/')
    ids = [x['id'] for x in (r.json or {}).get('results', [])]
    rec(f'MT-BS-01-{papel[:3]}', 'GET /barbershops/', papel, 'A', 'B', 'listar barbearias', 'só [A]', f'{r.status} {ids}', r.status == 200 and ids == [SHOP_A],
        f'GET /api/v1/barbershops/ como {papel} A', 'P0', A)
    r = s('GET', f'/barbershops/{SHOP_B}/')
    rec(f'MT-BS-02-{papel[:3]}', 'GET /barbershops/{id}/', papel, 'A', 'B', 'ler barbearia B', '404', short(r), r.status == 404,
        f'GET /api/v1/barbershops/<B>/ como {papel} A', 'P0', A)
h0 = row_hash('barbershops_barbershop', SHOP_B)
for tid, papel, s, metodo, corpo, desc in (
    ('MT-BS-03', 'admin', adminA, 'PATCH', {'nome': 'Invadida'}, 'renomear B'),
    ('MT-BS-04', 'admin', adminA, 'PUT', {'nome': 'X', 'endereco': 'X', 'telefone': '1', 'email': 'x@x.test', 'horario_abertura': '01:00', 'horario_fechamento': '02:00'}, 'substituir B (PUT)'),
    ('MT-BS-05', 'admin', adminA, 'PATCH', {'ativo': False}, 'desativar B'),
    ('MT-BS-06', 'admin', adminA, 'PATCH', {'dias_funcionamento': [1]}, 'mudar dias de B'),
    ('MT-BS-07', 'barbeiro', barbA, 'PATCH', {'nome': 'Invadida'}, 'renomear B'),
    ('MT-BS-08', 'cliente', cliA, 'PATCH', {'nome': 'Invadida'}, 'renomear B'),
):
    r = s(metodo, f'/barbershops/{SHOP_B}/', corpo)
    rec(tid, f'{metodo} /barbershops/{{id}}/', papel, 'A', 'B', desc, '403/404 e B inalterada', f'{short(r)}; inalterada={row_hash("barbershops_barbershop", SHOP_B) == h0}',
        denied(r) and row_hash('barbershops_barbershop', SHOP_B) == h0, f'{metodo} /api/v1/barbershops/<B>/ {json.dumps(corpo, ensure_ascii=False)}; conferir linha de B', 'P0', A)
raw, ct = multipart({}, {'logo': ('logo-invasor.png', PNG, 'image/png')})
r = adminA('PATCH', f'/barbershops/{SHOP_B}/', raw=raw, content_type=ct)
rec('MT-BS-09', 'PATCH /barbershops/{id}/ (multipart logo)', 'admin', 'A', 'B', 'trocar logo de B', '404 e logo de B inalterado', f'{short(r)}; inalterada={row_hash("barbershops_barbershop", SHOP_B) == h0}',
    denied(r) and row_hash('barbershops_barbershop', SHOP_B) == h0, 'PATCH multipart logo em /api/v1/barbershops/<B>/', 'P0', A)
nome_b = q1('select nome from barbershops_barbershop where id=%s', SHOP_B)
r = adminA('DELETE', f'/barbershops/{SHOP_B}/?confirmar={urllib.parse.quote(nome_b)}')
rec('MT-BS-10', 'DELETE /barbershops/{id}/', 'admin', 'A', 'B', 'desativar B com confirmação correta', '403/404 e B ativa', f'{short(r)}; ativa={q1("select ativo from barbershops_barbershop where id=%s", SHOP_B)}',
    denied(r) and row_hash('barbershops_barbershop', SHOP_B) == h0, 'DELETE /api/v1/barbershops/<B>/?confirmar=<nome de B>', 'P0', A)
n0 = q1('select count(*) from barbershops_barbershop')
r = cliA('POST', '/barbershops/', {'nome': 'Fuga', 'endereco': 'X', 'telefone': '1', 'email': 'f@x.test', 'horario_abertura': '09:00', 'horario_fechamento': '18:00'})
rec('MT-BS-11', 'POST /barbershops/', 'cliente', 'A', 'nova', 'cliente de A cria outra barbearia (troca de tenant)', '400; nenhuma barbearia nova; cliente continua em A',
    f'{short(r)}; barbearias {n0}->{q1("select count(*) from barbershops_barbershop")}; tenant={q1("select barbershop_id from accounts_user where id=%s", CLI_A1)}',
    r.status == 400 and q1('select count(*) from barbershops_barbershop') == n0 and q1('select barbershop_id from accounts_user where id=%s', CLI_A1) == SHOP_A,
    'POST /api/v1/barbershops/ como cliente A', 'P1', A)
hA = row_hash('barbershops_barbershop', SHOP_A)
r = adminA('PATCH', f'/barbershops/{SHOP_A}/', {'id': SHOP_B})
rec('MT-BS-12', 'PATCH /barbershops/{id}/', 'admin', 'A', 'B', 'enviar id=B no corpo da própria barbearia', 'id ignorado; A e B inalteradas',
    f'{short(r)}; A inalterada={row_hash("barbershops_barbershop", SHOP_A) == hA}; B inalterada={row_hash("barbershops_barbershop", SHOP_B) == h0}',
    row_hash('barbershops_barbershop', SHOP_B) == h0 and (r.json or {}).get('id') == SHOP_A, 'PATCH /api/v1/barbershops/<A>/ {"id": <B>}', 'P0', A)
logo_b_path = q1('select logo from barbershops_barbershop where id=%s', SHOP_B)
r = adminA('PATCH', f'/barbershops/{SHOP_A}/', {'logo': logo_b_path})
logo_a = q1('select logo from barbershops_barbershop where id=%s', SHOP_A)
rec('MT-BS-13', 'PATCH /barbershops/{id}/ (logo como texto)', 'admin', 'A', 'B', 'apontar o logo de A para o arquivo de B', '400; logo de A não aponta para o arquivo de B',
    f'{short(r)}; logo de A={"arquivo de B" if logo_a == logo_b_path else "outro"}', r.status == 400 and logo_a != logo_b_path,
    'PATCH /api/v1/barbershops/<A>/ {"logo": "<caminho do logo de B>"}', 'P2', A)
r = sem('GET', '/barbershops/')
r2 = sem('GET', f'/barbershops/{SHOP_B}/')
rec('MT-BS-14', 'GET /barbershops/', 'sem barbearia', '—', 'A/B', 'listar e ler barbearias', 'lista vazia; 404', f'lista={[x["id"] for x in (r.json or {}).get("results", [])]}; B={r2.status}',
    r.status == 200 and not (r.json or {}).get('results') and r2.status == 404, 'GET /api/v1/barbershops/ e /barbershops/<B>/ como usuário do cadastro público', 'P0', A)

# Onboarding de um segundo usuário sem barbearia tentando "entrar" em B
OB_EMAIL, OB_PW = 'onboarding@exemplo.test', 'Iso-' + secrets.token_urlsafe(14)
http('POST', '/auth/register/', body={'email': OB_EMAIL, 'nome': 'Onboarding Fictício', 'password': OB_PW})
ob = U(OB_EMAIL, OB_PW)
r = ob('POST', '/barbershops/', {'id': SHOP_B, 'nome': 'Barbearia C Fictícia', 'endereco': 'X', 'telefone': '1', 'email': 'c@x.test',
                                 'horario_abertura': '09:00', 'horario_fechamento': '18:00'})
SHOP_C = (r.json or {}).get('id')
ob_row = q('select barbershop_id, tipo_perfil from accounts_user where email=%s', OB_EMAIL)
rec('MT-BS-15', 'POST /barbershops/ (onboarding)', 'sem barbearia', '—', 'B', 'criar barbearia enviando id=B', '201 numa barbearia NOVA; usuário vira admin dela, não de B',
    f'{r.status} id={SHOP_C}; usuário={ob_row}', r.status == 201 and SHOP_C not in (SHOP_A, SHOP_B) and ob_row == [(SHOP_C, 'admin')],
    'POST /api/v1/barbershops/ {"id": <B>, ...} como usuário do cadastro público', 'P0', A)
obA = U(OB_EMAIL, OB_PW)
r = obA('GET', '/users/')
emails_c = {x['email'] for x in (r.json or {}).get('results', [])}
rec('MT-BS-16', 'GET /users/', 'admin (barbearia C recém-criada)', 'C', 'A/B', 'listar usuários', 'só o próprio admin de C', f'{r.status} {len(emails_c)} usuário(s); só C={emails_c == {OB_EMAIL}}',
    r.status == 200 and emails_c == {OB_EMAIL}, 'GET /api/v1/users/ como admin da barbearia criada no onboarding', 'P0', A)

# ===========================================================================
# 2. Usuários, clientes e barbeiros (contas)
# ===========================================================================
A = 'Usuários'
r = adminA('GET', '/users/?page_size=1000')
lista = []
pagina = r
while True:
    lista += [x['id'] for x in (pagina.json or {}).get('results', [])]
    nxt = (pagina.json or {}).get('next')
    if not nxt:
        break
    pagina = http('GET', nxt, adminA.token)
fora = q('select count(*) from accounts_user where id = any(%s) and (barbershop_id is distinct from %s)', lista, SHOP_A)[0][0]
rec('MT-US-01', 'GET /users/', 'admin', 'A', 'B', 'listar usuários (todas as páginas)', 'só usuários de A; total = banco', f'{len(lista)} itens; fora de A={fora}; banco A={q1("select count(*) from accounts_user where barbershop_id=%s", SHOP_A)}',
    fora == 0 and len(lista) == q1('select count(*) from accounts_user where barbershop_id=%s', SHOP_A), 'GET /api/v1/users/ (seguindo next) como admin A; comparar com accounts_user', 'P0', A)
r = adminA('GET', f'/users/?barbershop={SHOP_B}&barbershop_id={SHOP_B}&tipo_perfil=admin&search=B')
fora = q1('select count(*) from accounts_user where id = any(%s) and barbershop_id is distinct from %s', [x['id'] for x in (r.json or {}).get('results', [])], SHOP_A)
rec('MT-US-02', 'GET /users/?barbershop=…', 'admin', 'A', 'B', 'filtros barbershop/barbershop_id/tipo_perfil/search apontando para B', 'nenhum usuário de B', f'{r.status}; fora de A={fora}', r.status == 200 and fora == 0,
    'GET /api/v1/users/?barbershop=<B>&barbershop_id=<B>&tipo_perfil=admin&search=B', 'P0', A)
for n_alvo, (alvo_id, nome) in enumerate(((ADMIN_B, 'admin B'), (CLI_B, 'cliente B'), (BARBER_B_USER, 'barbeiro B'), (SUPER, 'superusuário'), (SEM_ID, 'usuário sem barbearia')), start=1):
    for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
        r = s('GET', f'/users/{alvo_id}/')
        rec(f'MT-US-03.{n_alvo}-{papel[:3]}','GET /users/{id}/', papel, 'A', 'B' if 'B' in nome else '—',
            f'ler {nome}', '404', short(r), r.status == 404, f'GET /api/v1/users/<{nome}>/ como {papel} A', 'P0', A)
hcb, hab = row_hash('accounts_user', CLI_B), row_hash('accounts_user', ADMIN_B)
for tid, papel, s, metodo, alvo_id, corpo, desc in (
    ('MT-US-04', 'admin', adminA, 'PATCH', CLI_B, {'nome': 'Invadido'}, 'renomear cliente B'),
    ('MT-US-05', 'admin', adminA, 'PATCH', CLI_B, {'is_active': False}, 'desativar cliente B'),
    ('MT-US-06', 'admin', adminA, 'PATCH', CLI_B, {'email': 'roubo@exemplo.test'}, 'trocar e-mail de login do cliente B'),
    ('MT-US-07', 'admin', adminA, 'PUT', CLI_B, {'email': 'roubo@exemplo.test', 'nome': 'X', 'tipo_perfil': 'cliente', 'is_active': True}, 'substituir cliente B'),
    ('MT-US-08', 'admin', adminA, 'DELETE', CLI_B, None, 'desativar cliente B (DELETE)'),
    ('MT-US-09', 'admin', adminA, 'DELETE', ADMIN_B, None, 'desativar admin B'),
    ('MT-US-10', 'admin', adminA, 'PATCH', ADMIN_B, {'tipo_perfil': 'cliente'}, 'rebaixar admin B'),
    ('MT-US-11', 'barbeiro', barbA, 'PATCH', CLI_B, {'nome': 'Invadido'}, 'renomear cliente B'),
    ('MT-US-12', 'cliente', cliA, 'PATCH', CLI_B, {'nome': 'Invadido'}, 'renomear cliente B'),
    ('MT-US-13', 'cliente', cliA, 'DELETE', CLI_B, None, 'desativar cliente B'),
):
    r = s(metodo, f'/users/{alvo_id}/', corpo)
    ok_db = row_hash('accounts_user', CLI_B) == hcb and row_hash('accounts_user', ADMIN_B) == hab
    rec(tid, f'{metodo} /users/{{id}}/', papel, 'A', 'B', desc, '403/404 e conta de B inalterada', f'{short(r)}; inalterada={ok_db}', denied(r) and ok_db,
        f'{metodo} /api/v1/users/<{"cliente B" if alvo_id == CLI_B else "admin B"}>/ {json.dumps(corpo, ensure_ascii=False) if corpo else ""}', 'P0', A)
nB = q1('select count(*) from accounts_user where barbershop_id=%s', SHOP_B)
r = adminA('POST', '/users/', {'email': 'novo.a1@exemplo.test', 'nome': 'Novo A1', 'password': 'Iso-' + secrets.token_urlsafe(12), 'tipo_perfil': 'cliente', 'barbershop': SHOP_B})
loc = q1('select barbershop_id from accounts_user where email=%s', 'novo.a1@exemplo.test')
rec('MT-US-14', 'POST /users/', 'admin', 'A', 'B', 'criar cliente com barbershop=B no corpo', '201 em A (campo ignorado); B sem usuário novo', f'{r.status}; criado em={"A" if loc == SHOP_A else loc}; usuários de B {nB}->{q1("select count(*) from accounts_user where barbershop_id=%s", SHOP_B)}',
    r.status == 201 and loc == SHOP_A and q1('select count(*) from accounts_user where barbershop_id=%s', SHOP_B) == nB, 'POST /api/v1/users/ {..., "barbershop": <B>}', 'P0', A)
r = adminA('POST', '/users/', {'email': 'novo.a2@exemplo.test', 'nome': 'Novo A2', 'password': 'Iso-' + secrets.token_urlsafe(12), 'tipo_perfil': 'barbeiro', 'especialidade': 'X', 'barbershop': SHOP_B})
loc = q('select u.barbershop_id, b.barbershop_id from accounts_user u left join barbershops_barber b on b.user_id=u.id where u.email=%s', 'novo.a2@exemplo.test')
rec('MT-US-15', 'POST /users/', 'admin', 'A', 'B', 'criar barbeiro com barbershop=B no corpo', '201; usuário e perfil em A', f'{r.status}; (usuário, perfil)={loc}', r.status == 201 and loc == [(SHOP_A, SHOP_A)],
    'POST /api/v1/users/ {tipo_perfil:"barbeiro", especialidade, barbershop:<B>}', 'P0', A)
email_b = q1('select email from accounts_user where id=%s', CLI_B)
r = adminA('POST', '/users/', {'email': email_b, 'nome': 'Clone', 'password': 'Iso-' + secrets.token_urlsafe(12), 'tipo_perfil': 'cliente'})
r_inex = adminA('POST', '/users/', {'email': 'inexistente.' + secrets.token_hex(3) + '@exemplo.test', 'nome': 'Clone', 'password': '1', 'tipo_perfil': 'cliente'})
rec('MT-US-16', 'POST /users/', 'admin', 'A', 'B', 'criar usuário com o e-mail de um cliente de B', 'recusa sem revelar que o e-mail existe em outra barbearia',
    f'{short(r)} | e-mail livre (senha inválida): {short(r_inex)}', r.status == 400 and 'email' not in (r.json or {}),
    'POST /api/v1/users/ {email:<e-mail do cliente B>} e comparar com e-mail inexistente', 'P3', A)
hc1 = row_hash('accounts_user', CLI_A1)
for tid, corpo, desc in (
    ('MT-US-17', {'tipo_perfil': 'admin'}, 'cliente se promove a admin'),
    ('MT-US-18', {'tipo_perfil': 'barbeiro'}, 'cliente se promove a barbeiro'),
    ('MT-US-19', {'barbershop': SHOP_B}, 'cliente se move para B'),
    ('MT-US-20', {'is_staff': True, 'is_superuser': True}, 'cliente se dá staff/superusuário'),
    ('MT-US-21', {'is_active': True, 'id': CLI_B}, 'cliente envia id de B no corpo'),
):
    r = cliA('PATCH', f'/users/{CLI_A1}/', corpo)
    row = q('select tipo_perfil, barbershop_id, is_staff, is_superuser from accounts_user where id=%s', CLI_A1)
    rec(tid, 'PATCH /users/{próprio id}/', 'cliente', 'A', 'A/B', desc, 'papel, barbearia e flags inalterados', f'{short(r)}; banco={row}',
        row == [('cliente', SHOP_A, False, False)] and row_hash('accounts_user', CLI_B) == hcb, f'PATCH /api/v1/users/<próprio>/ {json.dumps(corpo)}', 'P0', A)
barbA_id = barbA.me['id']
r = barbA('PATCH', f'/users/{barbA_id}/', {'tipo_perfil': 'admin', 'barbershop': SHOP_B, 'is_staff': True})
row = q('select tipo_perfil, barbershop_id, is_staff from accounts_user where id=%s', barbA_id)
rec('MT-US-22', 'PATCH /users/{próprio id}/', 'barbeiro', 'A', 'B', 'barbeiro se promove a admin e se move para B', 'inalterado', f'{short(r)}; banco={row}', row == [('barbeiro', SHOP_A, False)],
    'PATCH /api/v1/users/<próprio>/ {tipo_perfil:"admin", barbershop:<B>, is_staff:true}', 'P0', A)
for tid, corpo, desc, esperado_status in (
    ('MT-US-23', {'tipo_perfil': 'cliente'}, 'admin se rebaixa', (400,)),
    ('MT-US-24', {'barbershop': SHOP_B}, 'admin se move para B', None),
    ('MT-US-25', {'is_staff': True, 'is_superuser': True}, 'admin se dá staff/superusuário', None),
):
    r = adminA('PATCH', f'/users/{ADMIN_A}/', corpo)
    row = q('select tipo_perfil, barbershop_id, is_staff, is_superuser from accounts_user where id=%s', ADMIN_A)
    rec(tid, 'PATCH /users/{próprio id}/', 'admin', 'A', 'A/B', desc, 'inalterado' + (' (400)' if esperado_status else ''), f'{short(r)}; banco={row}',
        row == [('admin', SHOP_A, False, False)] and (esperado_status is None or r.status in esperado_status), f'PATCH /api/v1/users/<próprio>/ {json.dumps(corpo)}', 'P0', A)
alvo = CLIS_A[2]
r = adminA('PATCH', f'/users/{alvo}/', {'tipo_perfil': 'admin'})
r2 = adminA('PATCH', f'/users/{alvo}/', {'barbershop': SHOP_B})
row = q('select tipo_perfil, barbershop_id from accounts_user where id=%s', alvo)
rec('MT-US-26', 'PATCH /users/{id}/', 'admin', 'A', 'B', 'admin promove cliente de A a admin e o move para B', '400 na promoção; barbearia inalterada', f'{short(r)} | {short(r2)}; banco={row}',
    r.status == 400 and row == [('cliente', SHOP_A)], 'PATCH /api/v1/users/<cliente A>/ {tipo_perfil:"admin"} e {barbershop:<B>}', 'P0', A)
r = adminA('PATCH', f'/users/{alvo}/', {'email': email_b})
rec('MT-US-27', 'PATCH /users/{id}/', 'admin', 'A', 'B', 'dar a um cliente de A o e-mail de um cliente de B', 'recusa sem revelar a existência do e-mail', short(r),
    r.status == 400 and 'email' not in (r.json or {}), 'PATCH /api/v1/users/<cliente A>/ {email:<e-mail do cliente B>}', 'P3', A)
for papel, s, esperado in (('barbeiro', barbA, 403), ('cliente', cliA, 403), ('sem barbearia', sem, 403)):
    r = s('GET', '/users/')
    rec(f'MT-US-28-{papel[:3]}', 'GET /users/', papel, 'A' if papel != 'sem barbearia' else '—', 'A/B', 'listar usuários', '403', short(r), r.status == esperado,
        f'GET /api/v1/users/ como {papel}', 'P0', A)
r = sem('GET', '/users/me/')
rec('MT-US-29', 'GET /users/me/', 'sem barbearia', '—', '—', 'ler o próprio cadastro', '200 sem barbearia, cliente', f'{r.status} barbershop={(r.json or {}).get("barbershop")} perfil={(r.json or {}).get("tipo_perfil")}',
    r.status == 200 and (r.json or {}).get('barbershop') is None and (r.json or {}).get('tipo_perfil') == 'cliente', 'GET /api/v1/users/me/', 'P0', A)

# ===========================================================================
# 3. Barbeiros (perfil profissional)
# ===========================================================================
A = 'Barbeiros'
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    for params in ('', f'?ativo=all&barbershop={SHOP_B}', '?ativo=false'):
        r = s('GET', '/barbers/' + params)
        ids = [x['id'] for x in (r.json or {}).get('results', [])]
        fora = q1('select count(*) from barbershops_barber where id = any(%s) and barbershop_id <> %s', ids, SHOP_A)
        rec(f'MT-BA-01-{papel[:3]}{params[:8]}', f'GET /barbers/{params}', papel, 'A', 'B', 'listar barbeiros', 'nenhum barbeiro de B', f'{r.status}; {len(ids)} itens; de fora={fora}',
            r.status == 200 and fora == 0, f'GET /api/v1/barbers/{params} como {papel} A', 'P0', A)
    r = s('GET', f'/barbers/{BARBER_B}/')
    rec(f'MT-BA-02-{papel[:3]}', 'GET /barbers/{id}/', papel, 'A', 'B', 'ler barbeiro B', '404', short(r), r.status == 404, f'GET /api/v1/barbers/<barbeiro B>/ como {papel} A', 'P0', A)
hbb, hbbu = row_hash('barbershops_barber', BARBER_B), row_hash('accounts_user', BARBER_B_USER)
for tid, papel, s, metodo, corpo, desc in (
    ('MT-BA-03', 'admin', adminA, 'PATCH', {'especialidade': 'Invadido'}, 'editar barbeiro B'),
    ('MT-BA-04', 'admin', adminA, 'PATCH', {'ativo': False}, 'desativar barbeiro B (PATCH)'),
    ('MT-BA-05', 'admin', adminA, 'DELETE', None, 'desativar barbeiro B (DELETE)'),
    ('MT-BA-06', 'admin', adminA, 'PUT', {'user': BARBER_B_USER, 'especialidade': 'X', 'ativo': True}, 'substituir barbeiro B'),
    ('MT-BA-07', 'barbeiro', barbA, 'PATCH', {'especialidade': 'Invadido'}, 'editar barbeiro B'),
    ('MT-BA-08', 'cliente', cliA, 'DELETE', None, 'desativar barbeiro B'),
):
    r = s(metodo, f'/barbers/{BARBER_B}/', corpo)
    ok_db = row_hash('barbershops_barber', BARBER_B) == hbb and row_hash('accounts_user', BARBER_B_USER) == hbbu
    rec(tid, f'{metodo} /barbers/{{id}}/', papel, 'A', 'B', desc, '403/404; perfil e conta de B inalterados', f'{short(r)}; inalterado={ok_db}', denied(r) and ok_db,
        f'{metodo} /api/v1/barbers/<barbeiro B>/ {json.dumps(corpo, ensure_ascii=False) if corpo else ""}', 'P0', A)
nbar = q1('select count(*) from barbershops_barber')
for tid, alvo_id, nome in (('MT-BA-09', CLI_B, 'cliente B'), ('MT-BA-10', BARBER_B_USER, 'usuário do barbeiro B'), ('MT-BA-11', SEM_ID, 'usuário sem barbearia'), ('MT-BA-12', SUPER, 'superusuário')):
    h = row_hash('accounts_user', alvo_id)
    r = adminA('POST', '/barbers/', {'user': alvo_id, 'especialidade': 'X'})
    ok_db = row_hash('accounts_user', alvo_id) == h and q1('select count(*) from barbershops_barber') == nbar
    rec(tid, 'POST /barbers/', 'admin', 'A', 'B' if 'B' in nome else '—', f'promover {nome} a barbeiro de A', '400; conta alvo e perfis inalterados', f'{short(r)}; inalterado={ok_db}',
        r.status == 400 and ok_db, f'POST /api/v1/barbers/ {{"user": <{nome}>}}', 'P0', A)
alvo = CLIS_A[3]
r = adminA('POST', '/barbers/', {'user': alvo, 'especialidade': 'X', 'barbershop': SHOP_B})
loc = q('select b.barbershop_id, u.barbershop_id from barbershops_barber b join accounts_user u on u.id=b.user_id where b.user_id=%s', alvo)
rec('MT-BA-13', 'POST /barbers/', 'admin', 'A', 'B', 'promover cliente de A com barbershop=B no corpo', '201 com perfil em A', f'{r.status}; (perfil, usuário)={loc}', r.status == 201 and loc == [(SHOP_A, SHOP_A)],
    'POST /api/v1/barbers/ {"user": <cliente A>, "barbershop": <B>}', 'P0', A)
cb1 = cols('barbershops_barber', B1, 'user_id', 'barbershop_id', 'ativo')
r = adminA('PATCH', f'/barbers/{B1}/', {'user': CLI_B, 'barbershop': SHOP_B})
cb1b = cols('barbershops_barber', B1, 'user_id', 'barbershop_id', 'ativo')
rec('MT-BA-14', 'PATCH /barbers/{id}/', 'admin', 'A', 'B', 'trocar o usuário e a barbearia de um barbeiro de A para B', 'campos ignorados; usuário e barbearia do perfil inalterados', f'{r.status}; (user, barbearia, ativo) antes={cb1} depois={cb1b}',
    cb1 == cb1b, 'PATCH /api/v1/barbers/<barbeiro A>/ {"user": <cliente B>, "barbershop": <B>}', 'P0', A)
r = sem('GET', '/barbers/')
r2 = sem('GET', f'/barbers/{BARBER_B}/')
rec('MT-BA-15', 'GET /barbers/', 'sem barbearia', '—', 'A/B', 'listar e ler barbeiros', 'vazio; 404', f'{r.status} {len((r.json or {}).get("results", []))} itens; B={r2.status}',
    r.status == 200 and not (r.json or {}).get('results') and r2.status == 404, 'GET /api/v1/barbers/ como usuário do cadastro público', 'P0', A)

# ===========================================================================
# 4. Serviços e preços
# ===========================================================================
A = 'Serviços e preços'
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    for params in ('', f'?ativo=all&barbershop={SHOP_B}', '?ativo=false'):
        r = s('GET', '/services/' + params)
        ids = [x['id'] for x in (r.json or {}).get('results', [])]
        fora = q1('select count(*) from services_service where id = any(%s) and barbershop_id <> %s', ids, SHOP_A)
        rec(f'MT-SV-01-{papel[:3]}{params[:8]}', f'GET /services/{params}', papel, 'A', 'B', 'listar serviços', 'nenhum serviço de B', f'{r.status}; {len(ids)} itens; de fora={fora}',
            r.status == 200 and fora == 0, f'GET /api/v1/services/{params} como {papel} A', 'P0', A)
    for sid, nome in ((SVC_B, 'ativo'), (svc_b3, 'inativo')):
        r = s('GET', f'/services/{sid}/?ativo=all')
        rec(f'MT-SV-02-{papel[:3]}-{nome}', 'GET /services/{id}/', papel, 'A', 'B', f'ler serviço {nome} de B', '404', short(r), r.status == 404,
            f'GET /api/v1/services/<serviço {nome} B>/?ativo=all como {papel} A', 'P0', A)
hs, hs3 = row_hash('services_service', SVC_B), row_hash('services_service', svc_b3)
for tid, papel, s, metodo, sid, corpo, desc in (
    ('MT-SV-03', 'admin', adminA, 'PATCH', SVC_B, {'preco': '1.00'}, 'mudar o preço de B'),
    ('MT-SV-04', 'admin', adminA, 'PUT', SVC_B, {'nome': 'X', 'preco': '1.00', 'duracao': 5}, 'substituir serviço de B'),
    ('MT-SV-05', 'admin', adminA, 'DELETE', SVC_B, None, 'desativar serviço de B'),
    ('MT-SV-06', 'admin', adminA, 'PATCH', svc_b3, {'ativo': True}, 'reativar serviço inativo de B'),
    ('MT-SV-07', 'barbeiro', barbA, 'PATCH', SVC_B, {'preco': '1.00'}, 'mudar o preço de B'),
    ('MT-SV-08', 'cliente', cliA, 'DELETE', SVC_B, None, 'desativar serviço de B'),
):
    path = f'/services/{sid}/' + ('?ativo=all' if sid == svc_b3 else '')
    r = s(metodo, path, corpo)
    ok_db = row_hash('services_service', SVC_B) == hs and row_hash('services_service', svc_b3) == hs3
    rec(tid, f'{metodo} /services/{{id}}/', papel, 'A', 'B', desc, '403/404 e serviço inalterado', f'{short(r)}; inalterado={ok_db}', denied(r) and ok_db,
        f'{metodo} /api/v1{path} {json.dumps(corpo) if corpo else ""}', 'P0', A)
nsb = q1('select count(*) from services_service where barbershop_id=%s', SHOP_B)
r = adminA('POST', '/services/', {'nome': 'Criado por A', 'preco': '5.00', 'duracao': 30, 'barbershop': SHOP_B})
loc = q1('select barbershop_id from services_service where nome=%s', 'Criado por A')
rec('MT-SV-09', 'POST /services/', 'admin', 'A', 'B', 'criar serviço com barbershop=B no corpo', '201 em A; B sem serviço novo', f'{r.status}; criado em={"A" if loc == SHOP_A else loc}',
    r.status == 201 and loc == SHOP_A and q1('select count(*) from services_service where barbershop_id=%s', SHOP_B) == nsb, 'POST /api/v1/services/ {..., "barbershop": <B>}', 'P0', A)
hcorte = row_hash('services_service', CORTE)
r = adminA('PATCH', f'/services/{CORTE}/', {'barbershop': SHOP_B})
rec('MT-SV-10', 'PATCH /services/{id}/', 'admin', 'A', 'B', 'mover serviço de A para B', 'campo ignorado; serviço continua em A', f'{short(r)}; barbearia={q1("select barbershop_id from services_service where id=%s", CORTE)}',
    q1('select barbershop_id from services_service where id=%s', CORTE) == SHOP_A, 'PATCH /api/v1/services/<serviço A>/ {"barbershop": <B>}', 'P0', A)
r = sem('GET', '/services/')
r2 = sem('POST', '/services/', {'nome': 'X', 'preco': '1.00', 'duracao': 30})
rec('MT-SV-11', 'GET/POST /services/', 'sem barbearia', '—', 'A/B', 'listar e criar serviços', 'vazio; criação recusada', f'lista={len((r.json or {}).get("results", []))}; POST={r2.status}',
    r.status == 200 and not (r.json or {}).get('results') and r2.status in (403, 400), 'GET e POST /api/v1/services/ como usuário do cadastro público', 'P0', A)

# ===========================================================================
# 5. Agendamentos e histórico
# ===========================================================================
A = 'Agendamentos e histórico'


def todas(s, path):
    ids, r = [], s('GET', path)
    while r.status == 200:
        ids += [x['id'] for x in (r.json or {}).get('results', [])]
        nxt = (r.json or {}).get('next')
        if not nxt:
            break
        r = http('GET', nxt, s.token)
    return r.status, ids


esperado_scope = {
    'admin': q1('select count(*) from appointments_appointment where barbershop_id=%s', SHOP_A),
    'barbeiro': q1('select count(*) from appointments_appointment where barbeiro_id=%s', B1),
    'cliente': q1('select count(*) from appointments_appointment where cliente_id=%s', CLI_A1),
}
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    st_, ids = todas(s, '/appointments/')
    fora = q1('select count(*) from appointments_appointment where id = any(%s) and barbershop_id <> %s', ids, SHOP_A)
    rec(f'MT-AP-01-{papel[:3]}', 'GET /appointments/', papel, 'A', 'B', 'listar agendamentos (todas as páginas)', f'só o escopo do papel em A ({esperado_scope[papel]})',
        f'{st_}; {len(ids)} itens; de B={fora}', fora == 0 and len(ids) == esperado_scope[papel], f'GET /api/v1/appointments/ (seguindo next) como {papel} A; comparar com o banco', 'P0', A)
for tid, params in (('MT-AP-02a', f'?barbeiro={BARBER_B}'), ('MT-AP-02b', f'?servico={SVC_B}'), ('MT-AP-02c', f'?cliente={CLI_B}&barbershop={SHOP_B}'), ('MT-AP-02d', f'?status=agendado&barbershop_id={SHOP_B}')):
    r = adminA('GET', '/appointments/' + params)
    ids = [x['id'] for x in (r.json or {}).get('results', [])] if r.status == 200 else []
    fora = q1('select count(*) from appointments_appointment where id = any(%s) and barbershop_id <> %s', ids, SHOP_A)
    rec(tid, f'GET /appointments/{params}', 'admin', 'A', 'B', 'filtro apontando para objeto de B', 'nenhum agendamento de B', f'{r.status}; de B={fora}', fora == 0,
        f'GET /api/v1/appointments/{params}', 'P0', 'Relatórios, buscas e filtros')
r_b = adminA('GET', f'/appointments/?barbeiro={BARBER_B}')
r_x = adminA('GET', '/appointments/?barbeiro=999999')
rec('MT-FI-01', 'GET /appointments/?barbeiro=…', 'admin', 'A', 'B', 'comparar filtro com barbeiro de B e com ID inexistente', 'mesma resposta (sem oráculo)', f'B: {r_b.status} | inexistente: {short(r_x)}',
    r_b.status == r_x.status, 'GET /api/v1/appointments/?barbeiro=<barbeiro B> vs ?barbeiro=999999', 'P3', 'Relatórios, buscas e filtros')
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    for aid, nome in ((APPT_B, 'agendado'), (appt_b2, 'confirmado')):
        r = s('GET', f'/appointments/{aid}/')
        rec(f'MT-AP-03-{papel[:3]}-{nome[:4]}', 'GET /appointments/{id}/', papel, 'A', 'B', f'ler agendamento {nome} de B', '404', short(r), r.status == 404,
            f'GET /api/v1/appointments/<agendamento B>/ como {papel} A', 'P0', A)
ha1, ha2 = row_hash('appointments_appointment', APPT_B), row_hash('appointments_appointment', appt_b2)
for tid, papel, s, metodo, aid, corpo, desc in (
    ('MT-AP-04', 'admin', adminA, 'PATCH', APPT_B, {'observacoes': 'invadido'}, 'editar observação'),
    ('MT-AP-05', 'admin', adminA, 'PATCH', APPT_B, {'status': 'confirmado'}, 'confirmar'),
    ('MT-AP-06', 'admin', adminA, 'PATCH', appt_b2, {'data_hora': futuro(33, 9)}, 'remarcar'),
    ('MT-AP-07', 'admin', adminA, 'PUT', APPT_B, {'cliente': CLI_A1, 'barbeiro': B1, 'servico': CORTE, 'data_hora': futuro(33, 10)}, 'substituir apontando para A'),
    ('MT-AP-08', 'admin', adminA, 'DELETE', appt_b2, None, 'cancelar'),
    ('MT-AP-09', 'barbeiro', barbA, 'PATCH', APPT_B, {'status': 'confirmado'}, 'confirmar'),
    ('MT-AP-10', 'barbeiro', barbA, 'DELETE', APPT_B, None, 'cancelar'),
    ('MT-AP-11', 'cliente', cliA, 'PATCH', appt_b2, {'status': 'cancelado'}, 'cancelar por PATCH'),
    ('MT-AP-12', 'cliente', cliA, 'DELETE', appt_b2, None, 'cancelar por DELETE'),
    ('MT-AP-13', 'cliente', cliA, 'PATCH', APPT_B, {'cliente': CLI_A1}, 'tomar o agendamento para si'),
):
    r = s(metodo, f'/appointments/{aid}/', corpo)
    ok_db = row_hash('appointments_appointment', APPT_B) == ha1 and row_hash('appointments_appointment', appt_b2) == ha2
    rec(tid, f'{metodo} /appointments/{{id}}/', papel, 'A', 'B', f'{desc} um agendamento de B', '403/404 e agendamento inalterado', f'{short(r)}; inalterado={ok_db}', denied(r) and ok_db,
        f'{metodo} /api/v1/appointments/<agendamento B>/ {json.dumps(corpo) if corpo else ""}', 'P0', A)
nAB = q1('select count(*) from appointments_appointment where barbershop_id=%s', SHOP_B)
nAll = q1('select count(*) from appointments_appointment')
for tid, papel, s, corpo, desc in (
    ('MT-AP-14', 'admin', adminA, {'cliente': CLI_A1, 'barbeiro': BARBER_B, 'servico': CORTE, 'data_hora': futuro(34, 10)}, 'com barbeiro de B'),
    ('MT-AP-15', 'admin', adminA, {'cliente': CLI_A1, 'barbeiro': B1, 'servico': SVC_B, 'data_hora': futuro(34, 10)}, 'com serviço de B'),
    ('MT-AP-16', 'admin', adminA, {'cliente': CLI_B, 'barbeiro': B1, 'servico': CORTE, 'data_hora': futuro(34, 10)}, 'para cliente de B'),
    ('MT-AP-17', 'cliente', cliA, {'cliente': CLI_A1, 'barbeiro': BARBER_B, 'servico': SVC_B, 'data_hora': futuro(34, 11)}, 'com barbeiro e serviço de B'),
    ('MT-AP-18', 'barbeiro', barbA, {'cliente': CLI_B, 'servico': CORTE, 'data_hora': futuro(34, 12)}, 'para cliente de B'),
    ('MT-AP-19', 'barbeiro', barbA, {'cliente': CLI_A1, 'barbeiro': BARBER_B, 'servico': CORTE, 'data_hora': futuro(34, 13)}, 'na agenda do barbeiro de B'),
):
    r = s('POST', '/appointments/', corpo)
    ok_db = q1('select count(*) from appointments_appointment where barbershop_id=%s', SHOP_B) == nAB and q1('select count(*) from appointments_appointment') == nAll
    rec(tid, 'POST /appointments/', papel, 'A', 'B', f'criar agendamento {desc}', '400/403; nenhum agendamento criado', f'{short(r)}; nada criado={ok_db}', r.status in (400, 403) and ok_db,
        f'POST /api/v1/appointments/ {json.dumps(corpo)}', 'P0', A)
r = cliA('POST', '/appointments/', {'cliente': CLI_B, 'barbeiro': B1, 'servico': CORTE, 'data_hora': futuro(35, 10)})
dono = q('select cliente_id, barbershop_id from appointments_appointment where id=%s', (r.json or {}).get('id'))
rec('MT-AP-20', 'POST /appointments/', 'cliente', 'A', 'B', 'cliente A marca horário em nome do cliente B', '400, ou 201 em nome do próprio cliente A',
    f'{r.status}; dono={"cliente A" if dono == [(CLI_A1, SHOP_A)] else dono}', (r.status == 400) or (r.status == 201 and dono == [(CLI_A1, SHOP_A)]),
    'POST /api/v1/appointments/ {"cliente": <cliente B>, ...} como cliente A', 'P0', A)
r = adminA('POST', '/appointments/', {'cliente': CLI_A1, 'barbeiro': B3, 'servico': CORTE, 'data_hora': futuro(35, 11), 'barbershop': SHOP_B})
loc = q1('select barbershop_id from appointments_appointment where id=%s', (r.json or {}).get('id'))
rec('MT-AP-21', 'POST /appointments/', 'admin', 'A', 'B', 'criar com barbershop=B no corpo', '201 em A (campo ignorado)', f'{r.status}; criado em={"A" if loc == SHOP_A else loc}',
    r.status == 201 and loc == SHOP_A, 'POST /api/v1/appointments/ {..., "barbershop": <B>}', 'P0', A)
TCOLS = ('barbershop_id', 'cliente_id', 'barbeiro_id', 'servico_id', 'data_hora', 'status', 'preco_historico')
hown = cols('appointments_appointment', appt_a_admin, *TCOLS)
for tid, corpo, desc in (('MT-AP-22a', {'barbeiro': BARBER_B}, 'barbeiro de B'), ('MT-AP-22b', {'servico': SVC_B}, 'serviço de B'),
                         ('MT-AP-22c', {'cliente': CLI_B}, 'cliente de B'), ('MT-AP-22d', {'barbershop': SHOP_B}, 'barbearia B')):
    r = adminA('PATCH', f'/appointments/{appt_a_admin}/', corpo)
    rec(tid, 'PATCH /appointments/{id}/', 'admin', 'A', 'B', f'mover agendamento próprio para {desc}', '400 (ou campo ignorado); barbearia, cliente, barbeiro e serviço inalterados', f'{short(r)}; inalterado={cols("appointments_appointment", appt_a_admin, *TCOLS) == hown}',
        cols('appointments_appointment', appt_a_admin, *TCOLS) == hown, f'PATCH /api/v1/appointments/<agendamento A>/ {json.dumps(corpo)}', 'P0', A)
hcli = cols('appointments_appointment', appt_a, *TCOLS)
for tid, corpo, desc in (('MT-AP-23a', {'barbeiro': BARBER_B}, 'barbeiro de B'), ('MT-AP-23b', {'servico': SVC_B}, 'serviço de B'), ('MT-AP-23c', {'barbershop': SHOP_B}, 'barbearia B')):
    r = cliA('PATCH', f'/appointments/{appt_a}/', corpo)
    rec(tid, 'PATCH /appointments/{id}/', 'cliente', 'A', 'B', f'remarcar o próprio horário para {desc}', '400/403 (ou campo ignorado); barbearia, barbeiro e serviço inalterados', f'{short(r)}; inalterado={cols("appointments_appointment", appt_a, *TCOLS) == hcli}',
        cols('appointments_appointment', appt_a, *TCOLS) == hcli, f'PATCH /api/v1/appointments/<próprio>/ {json.dumps(corpo)}', 'P0', A)
nall0 = q1('select count(*) from appointments_appointment')
r = sem('GET', '/appointments/')
r2 = sem('POST', '/appointments/', {'cliente': SEM_ID, 'barbeiro': BARBER_B, 'servico': SVC_B, 'data_hora': futuro(36, 10)})
r3 = sem('GET', f'/appointments/{APPT_B}/')
rec('MT-AP-24', 'GET/POST /appointments/', 'sem barbearia', '—', 'B', 'listar, criar em B e ler agendamento de B', 'vazio; recusa (400/403) sem criar; 404', f'lista={len((r.json or {}).get("results", []))}; POST={short(r2)}; GET={r3.status}; criados={q1("select count(*) from appointments_appointment") - nall0}',
    r.status == 200 and not (r.json or {}).get('results') and r2.status in (400, 403) and r3.status == 404 and q1('select count(*) from appointments_appointment') == nall0, 'GET/POST /api/v1/appointments/ como usuário do cadastro público', 'P0', A)
ocupado = q1("select to_char(data_hora at time zone 'America/Sao_Paulo', 'YYYY-MM-DD\"T\"HH24:MI:SS-03:00') from appointments_appointment where id=%s", APPT_B)
livre = futuro(36, 11)
r_oc = sem('POST', '/appointments/', {'cliente': SEM_ID, 'barbeiro': BARBER_B, 'servico': SVC_B, 'data_hora': ocupado})
r_li = sem('POST', '/appointments/', {'cliente': SEM_ID, 'barbeiro': BARBER_B, 'servico': SVC_B, 'data_hora': livre})
rec('MT-AP-27', 'POST /appointments/ (validação)', 'sem barbearia', '—', 'B', 'tentar marcar com o barbeiro de B num horário ocupado e num livre', 'mesma recusa genérica nos dois (sem revelar a agenda de B)',
    f'ocupado: {short(r_oc)} | livre: {short(r_li)}; criados={q1("select count(*) from appointments_appointment") - nall0}', r_oc.status == r_li.status and r_oc.json == r_li.json,
    'POST /api/v1/appointments/ {cliente:<próprio>, barbeiro:<barbeiro B>, servico:<serviço B>, data_hora:<horário ocupado de B>} e o mesmo num horário livre', 'P2', A)
# Horizontal dentro da barbearia A (complemento)
r = cliA('GET', f'/appointments/{appt_a_other_cli}/')
r2 = cliA('PATCH', f'/appointments/{appt_a_other_cli}/', {'observacoes': 'x'})
rec('MT-AP-25', 'GET/PATCH /appointments/{id}/', 'cliente', 'A', 'A (outro cliente)', 'ler e editar agendamento de outro cliente da mesma barbearia', '404; 404', f'{r.status}; {r2.status}',
    r.status == 404 and r2.status == 404, 'GET e PATCH /api/v1/appointments/<agendamento de outro cliente de A>/', 'P1', A)
if appt_a_other_barber:
    h = row_hash('appointments_appointment', appt_a_other_barber)
    r = barbA('GET', f'/appointments/{appt_a_other_barber}/')
    r2 = barbA('PATCH', f'/appointments/{appt_a_other_barber}/', {'status': 'confirmado'})
    rec('MT-AP-26', 'GET/PATCH /appointments/{id}/', 'barbeiro', 'A', 'A (outro barbeiro)', 'ler e confirmar agendamento de outro barbeiro da mesma barbearia', '404; 404 e inalterado',
        f'{r.status}; {r2.status}; inalterado={row_hash("appointments_appointment", appt_a_other_barber) == h}', r.status == 404 and r2.status == 404 and row_hash('appointments_appointment', appt_a_other_barber) == h,
        'GET e PATCH /api/v1/appointments/<agendamento de outro barbeiro de A>/', 'P1', A)

# ===========================================================================
# 6. Disponibilidade e horários
# ===========================================================================
A = 'Disponibilidade e horários'
dia = (date.today() + timedelta(days=37)).isoformat()
for papel, s in (('admin', adminA), ('barbeiro', barbA), ('cliente', cliA)):
    for tid, params, desc in (('a', f'barbeiro={BARBER_B}&servico={CORTE}&data={dia}', 'barbeiro de B'),
                              ('b', f'barbeiro={B1}&servico={SVC_B}&data={dia}', 'serviço de B'),
                              ('c', f'barbeiro={BARBER_B}&servico={SVC_B}&data={dia}', 'barbeiro e serviço de B')):
        r = s('GET', f'/appointments/available-slots/?{params}')
        rec(f'MT-AV-01{tid}-{papel[:3]}', 'GET /appointments/available-slots/', papel, 'A', 'B', f'horários livres com {desc}', '404', short(r), r.status == 404,
            f'GET /api/v1/appointments/available-slots/?{params}', 'P0', A)
r = cliA('GET', f'/appointments/available-slots/?barbeiro={B1}&servico={CORTE}&data={dia}&exclude_appointment_id={appt_b2}')
r_x = cliA('GET', f'/appointments/available-slots/?barbeiro={B1}&servico={CORTE}&data={dia}&exclude_appointment_id=999999')
rec('MT-AV-02', 'GET /appointments/available-slots/?exclude_appointment_id=…', 'cliente', 'A', 'B', 'excluir agendamento de B da ocupação', '404 igual ao de ID inexistente', f'B: {short(r)} | inexistente: {short(r_x)}',
    r.status == 404 and r.json == r_x.json, 'GET …available-slots/?…&exclude_appointment_id=<agendamento B> vs 999999', 'P3', A)
r = sem('GET', f'/appointments/available-slots/?barbeiro={BARBER_B}&servico={SVC_B}&data={dia}')
rec('MT-AV-03', 'GET /appointments/available-slots/', 'sem barbearia', '—', 'B', 'horários livres de B', '403', short(r), r.status == 403, 'GET …available-slots/ como usuário do cadastro público', 'P0', A)
r_b = adminA('GET', f'/appointments/available-slots/?barbeiro={BARBER_B}&servico={CORTE}&data={dia}')
r_x = adminA('GET', f'/appointments/available-slots/?barbeiro=999999&servico={CORTE}&data={dia}')
rec('MT-AV-04', 'GET /appointments/available-slots/', 'admin', 'A', 'B', 'comparar barbeiro de B com ID inexistente', 'mesma resposta', f'B: {short(r_b)} | inexistente: {short(r_x)}',
    r_b.status == r_x.status and r_b.json == r_x.json, 'GET …available-slots/?barbeiro=<B> vs 999999', 'P3', A)

# ===========================================================================
# 7. Dashboards, indicadores e relatórios
# ===========================================================================
A = 'Dashboards e relatórios'
ini, fim = (date.today() - timedelta(days=60)).isoformat(), date.today().isoformat()
r = adminA('GET', f'/appointments/revenue-report/?start={ini}&end={fim}&barbershop={SHOP_B}')
esp = q1("select coalesce(sum(preco_historico),0)::text from appointments_appointment where barbershop_id=%s and status='realizado' and (data_hora at time zone 'America/Sao_Paulo')::date between %s and %s", SHOP_A, ini, fim)
nomes = {x['barbeiro'] for x in (r.json or {}).get('by_barber', [])} | {x['servico'] for x in (r.json or {}).get('by_service', [])}
rec('MT-RR-01', 'GET /appointments/revenue-report/', 'admin', 'A', 'B', 'faturamento (com barbershop=B na URL)', 'total = soma de A no banco; nenhum nome de B',
    f'{r.status}; total={(r.json or {}).get("total_revenue")} banco={esp}; nomes de B={[n for n in nomes if n in MARCAS_B]}',
    r.status == 200 and (r.json or {}).get('total_revenue') == esp and not [n for n in nomes if n in MARCAS_B], f'GET /api/v1/appointments/revenue-report/?start={ini}&end={fim}&barbershop=<B>', 'P0', A)
r = adminA('GET', f'/appointments/revenue-report/?start={ini}&end={fim}&barbeiro={BARBER_B}')
rec('MT-RR-02', 'GET /appointments/revenue-report/?barbeiro=…', 'admin', 'A', 'B', 'faturamento filtrando barbeiro de B', 'total 0', f'{r.status}; total={(r.json or {}).get("total_revenue")}',
    r.status == 200 and (r.json or {}).get('total_revenue') == '0.00', 'GET …revenue-report/?barbeiro=<barbeiro B>', 'P0', A)
for papel, s in (('barbeiro', barbA), ('cliente', cliA), ('sem barbearia', sem)):
    r = s('GET', '/appointments/revenue-report/')
    rec(f'MT-RR-03-{papel[:3]}', 'GET /appointments/revenue-report/', papel, 'A' if papel != 'sem barbearia' else '—', 'A/B', 'faturamento', '403', short(r), r.status == 403,
        f'GET /api/v1/appointments/revenue-report/ como {papel}', 'P0', A)
r = adminA('GET', '/appointments/?page=1')
cnt = (r.json or {}).get('count')
rec('MT-RR-04', 'GET /appointments/ (contagem do painel)', 'admin', 'A', 'B', 'contagem usada nos indicadores', 'igual ao total de A no banco',
    f'count={cnt}; banco A={q1("select count(*) from appointments_appointment where barbershop_id=%s", SHOP_A)}', cnt == q1('select count(*) from appointments_appointment where barbershop_id=%s', SHOP_A),
    'GET /api/v1/appointments/?page=1 (campo count)', 'P0', A)

# ===========================================================================
# 8. Uploads e mídia
# ===========================================================================
A = 'Uploads e imagens'
if LOGO_B_URL:
    caminho = urllib.parse.urlparse(LOGO_B_URL).path
    r = http('GET', ROOT + caminho, headers={'Accept': '*/*'})
    rec('MT-UP-01', 'GET /media/barbershops/logos/…', 'anônimo', '—', 'B', 'baixar o logo de B sem autenticação', 'documentar: arquivos de mídia são públicos por URL', f'{r.status} ({caminho})',
        r.status in (401, 403, 404), f'GET {caminho} sem Authorization', 'P3', A)
raw, ct = multipart({}, {'logo': ('../../../../fora-do-media.png', PNG, 'image/png')})
r = adminA('PATCH', f'/barbershops/{SHOP_A}/', raw=raw, content_type=ct)
logo_a = q1('select logo from barbershops_barbershop where id=%s', SHOP_A) or ''
rec('MT-UP-02', 'PATCH /barbershops/{id}/ (multipart)', 'admin', 'A', '—', 'upload com nome de arquivo com ../ (travessia de diretório)', 'nome saneado dentro de barbershops/logos/',
    f'{r.status}; gravado como {logo_a}', r.status == 200 and logo_a.startswith('barbershops/logos/') and '..' not in logo_a, 'PATCH multipart logo com filename="../../../../fora-do-media.png"', 'P1', A)

# ===========================================================================
# 9. API navegável do DRF e metadados (HTML)
# ===========================================================================
A = 'API navegável (HTML) e metadados'
SEL = re.compile(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', re.S)
OPT = re.compile(r'<option value="(\d+)"[^>]*>\s*(.*?)\s*</option>', re.S)
TAB = {'cliente': 'accounts_user', 'user': 'accounts_user', 'barbeiro': 'barbershops_barber', 'servico': 'services_service'}


def tenant_of(table, pk):
    if table == 'accounts_user':
        return q1('select barbershop_id from accounts_user where id=%s', pk)
    return q1(f'select barbershop_id from {table} where id=%s', pk)


def html_leak(s, path, origem):
    r = http('GET', path, s.token if s else None, headers={'Accept': 'text/html'})
    html = r.text
    alheios, por_campo = 0, {}
    for nome, corpo in SEL.findall(html):
        if nome not in TAB:
            continue
        for val, _txt in OPT.findall(corpo):
            t = tenant_of(TAB[nome], int(val))
            if t != origem:
                alheios += 1
                chave = f'{nome}:{"sem barbearia" if t is None else ("B" if t == SHOP_B else ("A" if t == SHOP_A else "C"))}'
                por_campo[chave] = por_campo.get(chave, 0) + 1
    marcas = [m for m in MARCAS_B if m in html] + (['Operador Plataforma'] if 'Operador Plataforma' in html else [])
    AMOSTRAS.update({f'{nome}:{txt}' for nome, corpo in SEL.findall(html) if nome in TAB for _v, txt in OPT.findall(corpo) if any(m in txt for m in MARCAS_B + ['Operador Plataforma'])})
    return r.status, alheios, por_campo, marcas


AMOSTRAS = set()


for tid, papel, s, origem, path in (
    ('MT-HT-01', 'cliente', cliA, SHOP_A, '/api/v1/appointments/'),
    ('MT-HT-02', 'barbeiro', barbA, SHOP_A, '/api/v1/appointments/'),
    ('MT-HT-03', 'admin', adminA, SHOP_A, '/api/v1/appointments/'),
    ('MT-HT-04', 'admin', adminA, SHOP_A, f'/api/v1/appointments/{appt_a_admin}/'),
    ('MT-HT-05', 'admin', adminA, SHOP_A, '/api/v1/barbers/'),
    ('MT-HT-06', 'admin', adminA, SHOP_A, f'/api/v1/barbers/{B1}/'),
    ('MT-HT-07', 'sem barbearia', sem, None, '/api/v1/appointments/'),
    ('MT-HT-08', 'admin (barbearia C, criada no onboarding)', obA, SHOP_C, '/api/v1/barbers/'),
    ('MT-HT-09', 'admin', adminA, SHOP_A, '/api/v1/users/'),
    ('MT-HT-10', 'admin', adminA, SHOP_A, '/api/v1/services/'),
    ('MT-HT-11', 'cliente', cliA, SHOP_A, '/api/v1/barbershops/'),
):
    st_, alheios, por_campo, marcas = html_leak(s, ROOT + path, origem)
    rec(tid, f'GET {path} (Accept: text/html)', papel, 'A' if origem == SHOP_A else ('C' if origem == SHOP_C else '—'), 'todas',
        'abrir a API navegável do DRF', 'nenhum registro de outra barbearia no HTML', f'{st_}; {alheios} opções de outros tenants {por_campo}; nomes de B no HTML={marcas}',
        alheios == 0 and not marcas, f'GET {path} com Authorization: Bearer <token de {papel}> e Accept: text/html; ler <select>/<option>', 'P0', A)
r = http('GET', f'{ROOT}/api/v1/appointments/?format=api', cliA.token, headers={'Accept': '*/*'})
rec('MT-HT-12', 'GET /api/v1/appointments/?format=api', 'cliente', 'A', 'todas', 'mesma página via ?format=api (sem cabeçalho Accept)', 'nenhum nome de B',
    f'{r.status}; nomes de B={[m for m in MARCAS_B if m in r.text]}', not [m for m in MARCAS_B if m in r.text], 'GET /api/v1/appointments/?format=api', 'P0', A)
r = http('OPTIONS', '/appointments/', cliA.token)
choices = json.dumps(r.json or {}, ensure_ascii=False)
rec('MT-HT-13', 'OPTIONS /appointments/ (JSON)', 'cliente', 'A', 'todas', 'metadados do endpoint', 'sem lista de clientes/barbeiros/serviços', f'{r.status}; nomes de B={[m for m in MARCAS_B if m in choices]}',
    not [m for m in MARCAS_B if m in choices], 'OPTIONS /api/v1/appointments/', 'P0', A)

# ===========================================================================
# 10. Autenticação, sessão e tokens
# ===========================================================================
A = 'Autenticação e sessão'
bl0 = SNAP_B0['token_blacklist_de_usuarios']
r = http('POST', '/auth/logout/', adminA.token, headers={'Cookie': f'barbearia_refresh={adminB.refresh}'})
bl1 = q1('select count(*) from token_blacklist_blacklistedtoken b join token_blacklist_outstandingtoken o on o.id=b.token_id join accounts_user u on u.id=o.user_id where u.barbershop_id=%s', SHOP_B)
rec('MT-AU-02', 'POST /auth/logout/', 'admin', 'A', 'B', 'encerrar a sessão do admin B usando o cookie de refresh dele', '400; nenhum token de B revogado', f'{short(r)}; revogados de B {bl0}->{bl1}',
    r.status == 400 and bl1 == bl0, 'POST /api/v1/auth/logout/ com Authorization de A e Cookie barbearia_refresh=<refresh de B>', 'P1', A)
partes = adminA.token.split('.')
payload = json.loads(base64.urlsafe_b64decode(partes[1] + '=' * (-len(partes[1]) % 4)))
payload.update({'barbershop_id': SHOP_B, 'tipo_perfil': 'admin', 'user_id': ADMIN_B})
forjado = partes[0] + '.' + base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=') + '.' + partes[2]
r = http('GET', '/users/me/', forjado)
rec('MT-AU-03', 'Authorization: Bearer (JWT adulterado)', 'admin', 'A', 'B', 'trocar user_id/barbershop_id no token sem reassinar', '401', short(r), r.status == 401,
    'JWT de A com payload alterado (user_id/barbershop_id de B) e assinatura original', 'P0', A)
r = http('GET', '/appointments/', None)
rec('MT-AU-04', 'GET /appointments/ (sem token)', 'anônimo', '—', 'todas', 'listar sem autenticação', '401', short(r), r.status == 401, 'GET /api/v1/appointments/ sem Authorization', 'P0', A)
anon = {p: http('GET', p).status for p in ('/users/', '/barbers/', '/services/', '/barbershops/', f'/appointments/available-slots/?barbeiro={BARBER_B}&servico={SVC_B}&data={dia}', '/appointments/revenue-report/')}
rec('MT-AU-05', 'demais endpoints (sem token)', 'anônimo', '—', 'todas', 'ler sem autenticação', '401 em todos', anon, all(v == 401 for v in anon.values()), 'GET em cada endpoint sem Authorization', 'P0', A)
hpw = q1('select password from accounts_user where id=%s', CLI_B)
uid = base64.urlsafe_b64encode(str(CLI_B).encode()).decode().rstrip('=')
r = http('POST', '/auth/password/reset/confirm/', body={'uid': uid, 'token': 'abc-123', 'new_password': 'Iso-' + secrets.token_urlsafe(12)})
rec('MT-AU-06', 'POST /auth/password/reset/confirm/', 'anônimo', '—', 'B', 'redefinir a senha do cliente B com token inventado', '400; senha inalterada', f'{short(r)}; senha inalterada={q1("select password from accounts_user where id=%s", CLI_B) == hpw}',
    r.status == 400 and q1('select password from accounts_user where id=%s', CLI_B) == hpw, 'POST /api/v1/auth/password/reset/confirm/ {uid:<cliente B>, token:"abc-123"}', 'P0', A)

# ===========================================================================
# 11. Django Admin
# ===========================================================================
A = 'Django Admin'
r = http('GET', ROOT + '/admin/', headers={'Accept': 'text/html'})
rec('MT-DA-01', 'GET /admin/', 'anônimo', '—', 'todas', 'abrir o Django Admin', '302 para o login', f'{r.status} → {r.headers.get("Location")}', r.status == 302 and '/admin/login/' in (r.headers.get('Location') or ''),
    'GET /admin/ sem sessão', 'P0', A)
for tid, email, papel in (('MT-DA-02', 'admin.a@exemplo.test', 'admin'), ('MT-DA-03', 'joao.barbeiro@exemplo.test', 'barbeiro'), ('MT-DA-04', 'cliente1@exemplo.test', 'cliente')):
    cj = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect)
    pg = http('GET', ROOT + '/admin/login/', headers={'Accept': 'text/html'}, opener=op)
    tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', pg.text).group(1)
    form = urllib.parse.urlencode({'csrfmiddlewaretoken': tok, 'username': email, 'password': CREDS[email], 'next': '/admin/'}).encode()
    r = http('POST', ROOT + '/admin/login/', raw=form, content_type='application/x-www-form-urlencoded', headers={'Accept': 'text/html', 'Referer': ROOT + '/admin/login/'}, opener=op)
    r2 = http('GET', ROOT + '/admin/accounts/user/', headers={'Accept': 'text/html'}, opener=op)
    rec(tid, 'POST /admin/login/', papel, 'A', 'todas', 'entrar no Django Admin com a própria senha', 'login recusado (não é staff); lista de usuários inacessível',
        f'login={r.status}; /admin/accounts/user/={r2.status} → {r2.headers.get("Location")}', r.status == 200 and r2.status == 302,
        'GET /admin/login/ (CSRF), POST /admin/login/ com e-mail e senha, GET /admin/accounts/user/', 'P0', A)
r = http('GET', ROOT + '/admin/autocomplete/?app_label=appointments&model_name=appointment&field_name=cliente&term=a', cliA.token, headers={'Accept': 'application/json'})
rec('MT-DA-05', 'GET /admin/autocomplete/', 'cliente (token da API)', 'A', 'todas', 'usar o autocomplete do admin com o token da API', '302/403 (sem sessão de staff)', f'{r.status}', r.status in (302, 403),
    'GET /admin/autocomplete/?app_label=appointments&model_name=appointment&field_name=cliente com Bearer', 'P0', A)

# ===========================================================================
# 12. Superusuário (operador da plataforma) — comportamento intencional
# ===========================================================================
A = 'Superusuário (plataforma)'
r = sup('GET', '/users/?page=1')
rec('MT-SU-01', 'GET /users/', 'superusuário', 'plataforma', 'todas', 'listar usuários', 'todas as barbearias (intencional: operador da plataforma)', f'{r.status}; count={(r.json or {}).get("count")}; banco={q1("select count(*) from accounts_user")}',
    r.status == 200 and (r.json or {}).get('count') == q1('select count(*) from accounts_user'), 'GET /api/v1/users/ como superusuário', '—', A)

# ===========================================================================
# 13. Integridade: fotografia de B antes x depois de todos os ataques de A
# ===========================================================================
SNAP_B1 = tenant_snapshot(SHOP_B)
dif = {k: (SNAP_B0[k], SNAP_B1[k]) for k in SNAP_B0 if SNAP_B0[k] != SNAP_B1[k]}
rec('MT-IN-01', 'banco (barbearia B inteira)', 'todos os papéis de A, sem barbearia e anônimo', 'A/—', 'B', 'comparar B antes e depois de todos os ataques',
    'nenhuma linha de B alterada, criada ou removida', f'tabelas diferentes={list(dif) or "nenhuma"}', not dif,
    'hash md5 de todas as linhas de B em barbershops_barbershop, accounts_user, barbershops_barber, services_service, appointments_appointment + tokens revogados de B', 'P0', 'Integridade dos dados')
rec('MT-IN-02', 'banco (usuário do cadastro público)', 'admin', 'A', '—', 'conta sem barbearia depois das tentativas de promoção', 'inalterada', f'inalterada={row_hash("accounts_user", SEM_ID) == SEM_ROW0}',
    row_hash('accounts_user', SEM_ID) == SEM_ROW0, 'hash da linha do usuário sem barbearia antes e depois', 'P0', 'Integridade dos dados')

# ===========================================================================
# 14. Sentido inverso: B atacando A (amostra), com fotografia de A
# ===========================================================================
A = 'Sentido inverso (B → A)'
SNAP_A0 = tenant_snapshot(SHOP_A)
for tid, s, papel, metodo, path, corpo in (
    ('MT-RV-01', adminB, 'admin', 'GET', f'/barbershops/{SHOP_A}/', None),
    ('MT-RV-02', adminB, 'admin', 'PATCH', f'/barbershops/{SHOP_A}/', {'nome': 'Invadida'}),
    ('MT-RV-03', adminB, 'admin', 'GET', f'/users/{ADMIN_A}/', None),
    ('MT-RV-04', adminB, 'admin', 'DELETE', f'/users/{CLI_A1}/', None),
    ('MT-RV-05', adminB, 'admin', 'PATCH', f'/services/{CORTE}/', {'preco': '1.00'}),
    ('MT-RV-06', adminB, 'admin', 'DELETE', f'/barbers/{B1}/', None),
    ('MT-RV-07', adminB, 'admin', 'PATCH', f'/appointments/{appt_a}/', {'status': 'confirmado'}),
    ('MT-RV-08', adminB, 'admin', 'DELETE', f'/appointments/{appt_a}/', None),
    ('MT-RV-09', barbB, 'barbeiro', 'PATCH', f'/appointments/{appt_a}/', {'status': 'confirmado'}),
    ('MT-RV-10', cliB, 'cliente', 'GET', f'/appointments/{appt_a}/', None),
    ('MT-RV-11', cliB, 'cliente', 'POST', '/appointments/', {'cliente': CLI_B, 'barbeiro': B1, 'servico': CORTE, 'data_hora': futuro(38, 10)}),
    ('MT-RV-12', adminB, 'admin', 'POST', '/barbers/', {'user': CLIS_A[4], 'especialidade': 'X'}),
):
    r = s(metodo, path, corpo)
    esperado = (400, 403, 404) if metodo == 'POST' else DENY
    rec(tid, f'{metodo} {path.split("?")[0]}', papel, 'B', 'A', f'{metodo} em objeto de A', '400/403/404', short(r), r.status in esperado,
        f'{metodo} /api/v1{path} {json.dumps(corpo) if corpo else ""} como {papel} B', 'P0', A)
SNAP_A1 = tenant_snapshot(SHOP_A)
dif = {k: (SNAP_A0[k], SNAP_A1[k]) for k in SNAP_A0 if SNAP_A0[k] != SNAP_A1[k]}
rec('MT-IN-03', 'banco (barbearia A inteira)', 'papéis de B', 'B', 'A', 'comparar A antes e depois dos ataques de B', 'nenhuma linha de A alterada', f'tabelas diferentes={list(dif) or "nenhuma"}', not dif,
    'mesma fotografia, para a barbearia A', 'P0', 'Integridade dos dados')

json.dump({'amostras_html': sorted(AMOSTRAS), 'alvo': {'api': ROOT, 'banco': f'{DB_ALVO[0]}@127.0.0.1:{DB_ALVO[1]}'}, 'resultados': OUT}, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
ok = sum(x['ok'] for x in OUT)
print(f'{len(OUT)} verificações; {ok} conforme; {len(OUT) - ok} divergentes')
for x in OUT:
    if not x['ok']:
        print(' X ', x['id'], x['severidade'], '|', x['papel'], '|', x['recurso'], '|', x['operacao'], '|', x['observado'][:230])
