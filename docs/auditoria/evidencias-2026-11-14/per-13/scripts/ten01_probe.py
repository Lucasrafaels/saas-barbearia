"""
TEN-01 (contenção) — sondagem HTTP da API navegável do DRF em todas as rotas, papéis e formas de pedir HTML.

Alvo: uma API ISOLADA (runserver, 127.0.0.1:876x) sobre o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432),
com o seed fictício da auditoria. Nunca aponta para o banco real. Não imprime nem grava senhas ou tokens.

Uso: python -I ten01_probe.py <estado_seed.json> <url_base> <rótulo> <saída.json>
"""
import json
import re
import secrets
import sys
import urllib.error
import urllib.request
from datetime import timedelta, date

import psycopg2

ST = json.load(open(sys.argv[1]))
BASE, ROTULO, SAIDA = sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4]
assert re.fullmatch(r'http://127\.0\.0\.1:87(67|68|69|70|71|72)', BASE), BASE
API = BASE + '/api/v1'
CREDS, IDS = ST['creds'], ST['ids']

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


ACCEPT_AXIOS = 'application/json, text/plain, */*'
ACCEPT_NAVEGADOR = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'


class Resp:
    def __init__(self, status, body, headers):
        self.status, self.body, self.headers = status, body, headers
        try:
            self.json = json.loads(body)
        except Exception:
            self.json = None


class SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(SemRedirecionar)


def http(metodo, url, token=None, corpo=None, accept=ACCEPT_AXIOS):
    h = {}
    if accept is not None:
        h['Accept'] = accept
    dados = None
    if token:
        h['Authorization'] = 'Bearer ' + token
    if corpo is not None:
        dados = json.dumps(corpo).encode()
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url if url.startswith('http') else API + url, data=dados, headers=h, method=metodo)
    if accept is None:
        # urllib não envia Accept por padrão; garante a ausência do cabeçalho.
        req.remove_header('Accept')
    try:
        r = OPENER.open(req, timeout=30)
        return Resp(r.status, r.read().decode('utf-8', 'replace'), dict(r.headers))
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.read().decode('utf-8', 'replace'), dict(e.headers))


def login(email, senha):
    r = http('POST', '/auth/login/', corpo={'email': email, 'password': senha})
    assert r.status == 200 and r.headers.get('Content-Type', '').startswith('application/json'), (email, r.status)
    return r.json['access']


# ---------------------------------------------------------------------------
# Papéis: A (origem), B (sentido inverso), conta do cadastro público, admin de uma barbearia criada no
# onboarding, superusuário e anônimo. As contas públicas são criadas nesta execução, pela própria API.
# ---------------------------------------------------------------------------
sufixo = secrets.token_hex(3)
SEM_EMAIL, SEM_PW = f'ten01.sem.{sufixo}@exemplo.test', 'T01-' + secrets.token_urlsafe(14)
OB_EMAIL, OB_PW = f'ten01.onboarding.{sufixo}@exemplo.test', 'T01-' + secrets.token_urlsafe(14)
for email, nome, senha in ((SEM_EMAIL, f'TEN01 Sem Barbearia {sufixo}', SEM_PW), (OB_EMAIL, f'TEN01 Onboarding {sufixo}', OB_PW)):
    r = http('POST', '/auth/register/', corpo={'email': email, 'nome': nome, 'password': senha})
    assert r.status == 201, ('cadastro', r.status, r.body[:200])
tok_ob = login(OB_EMAIL, OB_PW)
r = http('POST', '/barbershops/', tok_ob, {'nome': f'TEN01 Barbearia C {sufixo}', 'endereco': 'Rua C, 1', 'telefone': '1',
                                          'email': f'c.{sufixo}@exemplo.test', 'horario_abertura': '09:00', 'horario_fechamento': '18:00'})
assert r.status == 201, ('onboarding', r.status, r.body[:200])
SHOP_C = r.json['id']

SHOP_A, SHOP_B = IDS['shop_a'], IDS['shop_b']
SESSOES = {
    'anônimo': (None, None),
    'cliente A': (login('cliente1@exemplo.test', CREDS['cliente1@exemplo.test']), SHOP_A),
    'barbeiro A': (login('joao.barbeiro@exemplo.test', CREDS['joao.barbeiro@exemplo.test']), SHOP_A),
    'admin A': (login('admin.a@exemplo.test', CREDS['admin.a@exemplo.test']), SHOP_A),
    'cliente B': (login('cliente.b@exemplo.test', CREDS['cliente.b@exemplo.test']), SHOP_B),
    'admin B': (login('admin.b@exemplo.test', CREDS['admin.b@exemplo.test']), SHOP_B),
    'sem barbearia (cadastro público)': (login(SEM_EMAIL, SEM_PW), 'sem'),
    'admin C (onboarding)': (login(OB_EMAIL, OB_PW), SHOP_C),
    'superusuário': (login('plataforma@exemplo.test', CREDS['plataforma@exemplo.test']), 'plataforma'),
}
SEM_ID = q1('select id from accounts_user where email=%s', SEM_EMAIL)

# ---------------------------------------------------------------------------
# Marcas de cada tenant, lidas do banco: nomes e e-mails de usuários e barbearias. Cada conta sem barbearia é
# um "tenant" à parte; o superusuário é a plataforma.
# ---------------------------------------------------------------------------
def dono_usuario(uid, shop, su):
    if su:
        return 'plataforma'
    if shop is None:
        return 'sem' if uid == SEM_ID else f'sem:{uid}'
    return shop


MARCAS = []  # (dono, texto)
for uid, nome, email, shop, su in q('select id, nome, email, barbershop_id, is_superuser from accounts_user'):
    MARCAS += [(dono_usuario(uid, shop, su), nome), (dono_usuario(uid, shop, su), email)]
for sid, nome, email in q('select id, nome, email from barbershops_barbershop'):
    MARCAS += [(sid, nome), (sid, email)]
# Serviços de B com nome distinto (os de A, como "Corte", são substrings dos de B e gerariam falso positivo).
MARCAS += [(SHOP_B, n) for (n,) in q('select nome from services_service where barbershop_id=%s', SHOP_B)]


def marcas_alheias(corpo, dono):
    return sorted({t for d, t in MARCAS if d != dono and re.search(r'(?<![\w@.])' + re.escape(t) + r'(?![\w])', corpo)})


TAB = {'cliente': 'accounts_user', 'user': 'accounts_user', 'barbeiro': 'barbershops_barber', 'servico': 'services_service'}
SEL = re.compile(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', re.S)
OPT = re.compile(r'<option value="(\d+)"[^>]*>', re.S)


def opcoes_alheias(corpo, dono):
    contagem = {}
    for nome, bloco in SEL.findall(corpo):
        if nome not in TAB:
            continue
        for val in OPT.findall(bloco):
            if TAB[nome] == 'accounts_user':
                uid, shop, su = q('select id, barbershop_id, is_superuser from accounts_user where id=%s', int(val))[0]
                d = dono_usuario(uid, shop, su)
            else:
                d = q1(f'select barbershop_id from {TAB[nome]} where id=%s', int(val))
            if d != dono:
                chave = f'{nome}:{"B" if d == SHOP_B else "A" if d == SHOP_A else "C" if d == SHOP_C else d}'
                contagem[chave] = contagem.get(chave, 0) + 1
    return contagem


# ---------------------------------------------------------------------------
# Rotas e formas de pedir
# ---------------------------------------------------------------------------
B1 = IDS['barbers'][0]
CORTE = IDS['services'][0]
APPT_A = q1("select min(a.id) from appointments_appointment a join accounts_user u on u.id=a.cliente_id "
            "where a.barbershop_id=%s and u.email='cliente1@exemplo.test' and a.barbeiro_id=%s", SHOP_A, B1)
dia = date.today() + timedelta(days=3)
ROTAS = [  # nome, caminho, sufixos registrados ('rota', 'acao' ou None)
    ('raiz', '/api/v1/', 'rota'),
    ('usuários', '/api/v1/users/', 'rota'),
    ('usuário (admin A)', f'/api/v1/users/{IDS["admin_a"]}/', 'rota'),
    ('usuário atual', '/api/v1/users/me/', 'acao'),
    ('barbearias', '/api/v1/barbershops/', 'rota'),
    ('barbearia A', f'/api/v1/barbershops/{SHOP_A}/', 'rota'),
    ('barbeiros', '/api/v1/barbers/', 'rota'),
    ('barbeiro A', f'/api/v1/barbers/{B1}/', 'rota'),
    ('serviços', '/api/v1/services/', 'rota'),
    ('serviço A', f'/api/v1/services/{CORTE}/', 'rota'),
    ('agendamentos', '/api/v1/appointments/', 'rota'),
    ('agendamento A', f'/api/v1/appointments/{APPT_A}/', 'rota'),
    ('horários livres', f'/api/v1/appointments/available-slots/?barbeiro={B1}&servico={CORTE}&data={dia}', 'acao'),
    ('faturamento', '/api/v1/appointments/revenue-report/', 'acao'),
    ('auth: cadastro', '/api/v1/auth/register/', None),
    ('auth: login', '/api/v1/auth/login/', None),
    ('auth: refresh', '/api/v1/auth/refresh/', None),
    ('auth: logout', '/api/v1/auth/logout/', None),
    ('auth: troca de senha', '/api/v1/auth/password/change/', None),
    ('auth: recuperação', '/api/v1/auth/password/reset/', None),
    ('auth: confirmação', '/api/v1/auth/password/reset/confirm/', None),
]
VARIANTES = [  # nome, tipo, Accept, ?format=, sufixo
    ('Accept: text/html', 'html', 'text/html', None, None),
    ('Accept: text/html,application/xhtml+xml', 'html', 'text/html,application/xhtml+xml', None, None),
    ('?format=api', 'html', '*/*', 'api', None),
    ('?format=api + Accept: text/html', 'html', 'text/html', 'api', None),
    ('sufixo .api', 'html', '*/*', None, 'api'),
    ('Accept de navegador', 'navegador', ACCEPT_NAVEGADOR, None, None),
    ('Accept: application/json', 'json', 'application/json', None, None),
    ('Accept padrão do axios', 'json', ACCEPT_AXIOS, None, None),
    ('sem Accept', 'json', None, None, None),
    ('?format=json', 'json', '*/*', 'json', None),
    ('sufixo .json', 'json', '*/*', None, 'json'),
]


def montar(caminho, formato, sufixo):
    base, _, consulta = caminho.partition('?')
    if sufixo:
        base = '/api/v1/.' + sufixo if base == '/api/v1/' else base.rstrip('/') + '.' + sufixo
    if formato:
        consulta = (consulta + '&' if consulta else '') + 'format=' + formato
    return BASE + base + ('?' + consulta if consulta else '')


OUT = []
for rota, caminho, sufixos in ROTAS:
    for variante, tipo, accept, formato, sufixo in VARIANTES:
        if sufixo and (sufixos is None or (sufixo == 'json' and sufixos == 'acao')):
            # Sem rota com sufixo (auth) ou API-03 (sufixo .json nas @action responde 500 antes e depois).
            continue
        for papel, (token, dono) in SESSOES.items():
            r = http('GET', montar(caminho, formato, sufixo), token, accept=accept)
            ctype = r.headers.get('Content-Type', '')
            html = 'text/html' in ctype or bool(re.search(r'<\s*(html|form|select|option|!doctype)', r.body, re.I))
            alheias = marcas_alheias(r.body, dono) if dono != 'plataforma' else []
            opcoes = opcoes_alheias(r.body, dono) if html and dono != 'plataforma' else {}
            OUT.append({
                'rota': rota, 'caminho': caminho, 'variante': variante, 'tipo': tipo, 'papel': papel,
                'status': r.status, 'content_type': ctype.split(';')[0], 'bytes': len(r.body.encode()), 'html': html,
                'selects': len(SEL.findall(r.body)), 'opcoes_alheias': opcoes, 'marcas_alheias': alheias[:8],
                'n_marcas_alheias': len(alheias), 'corpo_json_detail': (list(r.json) == ['detail']) if isinstance(r.json, dict) else False,
            })

# OPTIONS em JSON (metadados): renderizadores anunciados e ausência de listas de registros.
r = http('OPTIONS', '/appointments/', SESSOES['cliente A'][0])
OPTIONS = {'status': r.status, 'renders': (r.json or {}).get('renders'), 'marcas_alheias': marcas_alheias(r.body, SHOP_A)}

json.dump({'rotulo': ROTULO, 'api': BASE, 'banco': f'{alvo[0]}@127.0.0.1:{alvo[1]}', 'options': OPTIONS, 'resultados': OUT},
          open(SAIDA, 'w'), ensure_ascii=False, indent=1)
html = [x for x in OUT if x['html']]
vaz = [x for x in OUT if x['n_marcas_alheias'] or x['opcoes_alheias']]
print(f'{ROTULO}: {len(OUT)} pedidos; respostas HTML={len(html)}; com dados de outro tenant={len(vaz)}; '
      f'500={sum(x["status"] >= 500 for x in OUT)}; OPTIONS renders={OPTIONS["renders"]}')
