"""
PER-13 — sondagem HTTP de GET/HEAD /api/v1/users/{id}/ por papel, com o SQL que o servidor executou para cada pedido
(log do PostgreSQL descartável com log_statement = 'all' e marcadores por pedido). Também registra PATCH em outro
usuário da mesma barbearia (achado separado SEC-12), com corpo vazio para não alterar nada.

Alvo: API ISOLADA (runserver, 127.0.0.1:8767-8770) sobre o banco DESCARTÁVEL iso_db (PG 18.3, 127.0.0.1:55432).
Não imprime nem grava senhas ou tokens.  Uso: python -I per13_probe.py <estado_seed.json> <url> <rótulo> <log_pg> <saída.json>
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


def http(metodo, caminho, token, corpo=None):
    h = {'Accept': 'application/json, text/plain, */*', 'Authorization': 'Bearer ' + token}
    dados = json.dumps(corpo).encode() if corpo is not None else None
    if dados is not None:
        h['Content-Type'] = 'application/json'
    try:
        r = urllib.request.urlopen(urllib.request.Request(API + caminho, data=dados, headers=h, method=metodo), timeout=30)
        return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def login(email, senha):
    req = urllib.request.Request(API + '/auth/login/', data=json.dumps({'email': email, 'password': senha}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=30).read())['access']


def foto_usuarios():
    return q1("select md5(string_agg(t::text, '|' order by id)) from accounts_user t")


PEDIDOS = []


def pedir(papel, alvo_rotulo, alvo_id, metodo, token, solicitante, corpo=None):
    marca = secrets.token_hex(6)
    q(f"select 'PER13-INICIO-{marca}'")
    status, resposta = http(metodo, f'/users/{alvo_id}/', token, corpo)
    q(f"select 'PER13-FIM-{marca}'")
    dados_alvo = q('select email, nome from accounts_user where id=%s', alvo_id)
    PEDIDOS.append({'papel': papel, 'alvo': alvo_rotulo, 'alvo_id': alvo_id, 'metodo': metodo, 'status': status,
                    'resposta': resposta[:200], 'marca': marca, 'solicitante': solicitante,
                    'dados_do_alvo_na_resposta': bool(dados_alvo) and alvo_rotulo != 'o próprio'
                    and any(x and x.lower() in resposta.lower() for x in dados_alvo[0])})


SHOP_A, SHOP_B = IDS['shop_a'], IDS['shop_b']


def usuario(email):
    return q1('select id from accounts_user where email=%s', email)


def de(shop, perfil, exceto):
    return q1('select id from accounts_user where barbershop_id=%s and tipo_perfil=%s and id <> %s and is_active order by id limit 1', shop, perfil, exceto)


PAPEIS = [('cliente A', 'cliente1@exemplo.test', SHOP_A, SHOP_B), ('barbeiro A', 'joao.barbeiro@exemplo.test', SHOP_A, SHOP_B),
          ('admin A', 'admin.a@exemplo.test', SHOP_A, SHOP_B), ('cliente B', 'cliente.b@exemplo.test', SHOP_B, SHOP_A),
          ('barbeiro B', 'barbeiro.b@exemplo.test', SHOP_B, SHOP_A), ('admin B', 'admin.b@exemplo.test', SHOP_B, SHOP_A),
          ('superusuário', 'plataforma@exemplo.test', None, None)]
FOTO0 = foto_usuarios()
for papel, email, proprio, outro in PAPEIS:
    token = login(email, CREDS[email])
    eu = usuario(email)
    alvos = [('o próprio', eu)]
    if proprio:
        alvos += [(f'{perfil} da mesma barbearia', de(proprio, perfil, eu)) for perfil in ('cliente', 'barbeiro', 'admin')]
        alvos += [(f'{perfil} de outra barbearia', de(outro, perfil, eu)) for perfil in ('cliente', 'barbeiro', 'admin')]
    else:
        alvos += [('cliente A', usuario('cliente2@exemplo.test')), ('admin B', usuario('admin.b@exemplo.test'))]
    alvos.append(('inexistente', 999999))
    for rotulo, alvo_id in alvos:
        if alvo_id is None:
            continue
        for metodo in ('GET', 'HEAD'):
            pedir(papel, rotulo, alvo_id, metodo, token, eu)
        if papel.startswith(('cliente', 'barbeiro')) and rotulo != 'o próprio':
            pedir(papel, rotulo, alvo_id, 'PATCH', token, eu, {})  # SEC-12: corpo vazio, nada é alterado

# Conta do cadastro público (sem barbearia).
sufixo = secrets.token_hex(3)
email_sem, senha_sem = f'per13.sem.{sufixo}@exemplo.test', 'P13-' + secrets.token_urlsafe(14)
req = urllib.request.Request(API + '/auth/register/', data=json.dumps({'email': email_sem, 'nome': f'PER13 {sufixo}', 'password': senha_sem}).encode(),
                             headers={'Content-Type': 'application/json'}, method='POST')
urllib.request.urlopen(req, timeout=30)
FOTO0 = foto_usuarios()  # depois do cadastro público, que cria uma linha
tok_sem = login(email_sem, senha_sem)
sem_id = usuario(email_sem)
for rotulo, alvo_id in (('o próprio', sem_id), ('cliente A', usuario('cliente2@exemplo.test')), ('admin B', usuario('admin.b@exemplo.test')), ('inexistente', 999999)):
    for metodo in ('GET', 'HEAD'):
        pedir('sem barbearia', rotulo, alvo_id, metodo, tok_sem, sem_id)
FOTO1 = foto_usuarios()

log = open(LOG_PG, encoding='utf-8', errors='replace').read()
for p in PEDIDOS:
    m = re.search(rf"PER13-INICIO-{p['marca']}'(.*?)select 'PER13-FIM-{p['marca']}", log, re.S)
    comandos = [x for x in re.findall(r'LOG:\s+statement:\s+(.*)', m.group(1)) if re.match(r'\s*(SELECT|INSERT|UPDATE|DELETE)', x, re.I)] if m else []
    completos = [re.sub(r'SELECT .*? FROM', 'SELECT … FROM', x) for x in comandos if 'set_config' not in x]
    p['sql'] = [x[:400] for x in completos]
    busca = [x for x in completos if re.search(rf'"accounts_user"\."id" = {p["alvo_id"]}\b', x)]
    p['busca_do_alvo'] = [x[:400] for x in busca]
    p['busca_sem_barbearia'] = sum('"accounts_user"."barbershop_id" =' not in x.split(' WHERE ', 1)[-1] for x in busca)
    p['busca_sem_o_solicitante'] = sum(not re.search(rf'"accounts_user"\."id" = {p["solicitante"]}\b', x.split(' WHERE ', 1)[-1]) for x in busca)
    p['_norm'] = [re.sub(r'\d+', '<n>', x) for x in completos]

resumo = {}
for papel in dict.fromkeys(p['papel'] for p in PEDIDOS):
    gets = [p for p in PEDIDOS if p['papel'] == papel and p['metodo'] == 'GET']
    heads = [p for p in PEDIDOS if p['papel'] == papel and p['metodo'] == 'HEAD']
    inexistente = next(p for p in gets if p['alvo'] == 'inexistente')
    autorizados = {'admin': lambda p: 'da mesma barbearia' in p['alvo'] or p['alvo'] == 'o próprio',
                   'superusuário': lambda p: p['alvo'] != 'inexistente'}
    pode = autorizados.get(papel.split()[0], lambda p: p['alvo'] == 'o próprio' and papel != 'sem barbearia')
    nao = [p for p in gets if not pode(p) and p['alvo'] != 'inexistente']
    resumo[papel] = {
        'GET autorizados': {p['alvo']: p['status'] for p in gets if pode(p)},
        'GET não autorizados': len(nao),
        'GET não autorizados com resposta diferente da do inexistente': sum((p['status'], p['resposta']) != (inexistente['status'], inexistente['resposta']) for p in nao),
        'GET não autorizados com SQL diferente da do inexistente (só números mudam)': sum(p['_norm'] != inexistente['_norm'] for p in nao),
        'HEAD não autorizados com status diferente do inexistente': sum(h['status'] != next(x for x in heads if x['alvo'] == 'inexistente')['status']
                                                                         for h in heads if not pode(h) and h['alvo'] != 'inexistente'),
        'respostas com dados do usuário consultado (não autorizados)': sum(p['dados_do_alvo_na_resposta'] for p in nao),
        'buscas do alvo sem condição de barbearia (não superusuário)': sum(p['busca_sem_barbearia'] for p in gets if papel != 'superusuário'),
        'buscas do alvo sem o solicitante no WHERE (cliente/barbeiro)': sum(p['busca_sem_o_solicitante'] for p in gets) if papel.startswith(('cliente', 'barbeiro')) else None,
        'PATCH em outro usuário da mesma barbearia x inexistente (SEC-12)': sorted({(p['alvo'], p['status']) for p in PEDIDOS if p['papel'] == papel and p['metodo'] == 'PATCH' and ('mesma' in p['alvo'] or p['alvo'] == 'inexistente')}),
    }
geral = {'pedidos': len(PEDIDOS), 'respostas_500': sum(p['status'] >= 500 for p in PEDIDOS), 'usuarios_inalterados': FOTO0 == FOTO1}
for p in PEDIDOS:
    p.pop('_norm', None)
json.dump({'rotulo': ROTULO, 'api': BASE, 'geral': geral, 'resumo': resumo, 'pedidos': PEDIDOS}, open(SAIDA, 'w'), ensure_ascii=False, indent=1)
print(f'== {ROTULO}: {json.dumps(geral, ensure_ascii=False)}')
for papel, r in resumo.items():
    print(f'   {papel}: {json.dumps(r, ensure_ascii=False)}')
