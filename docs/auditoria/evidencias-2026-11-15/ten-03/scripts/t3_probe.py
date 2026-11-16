#!/usr/bin/env python3
"""
TEN-03 — sondagem HTTP dos fluxos que recebem e-mail, contra a API de laboratório (código atual, sem
alteração, DEBUG=False) sobre o banco DESCARTÁVEL t3_db (PG 18.3, 127.0.0.1:55432).

Para cada cenário:
  1. restaura o estado do seed (apaga contas criadas, devolve os e-mails originais);
  2. fotografa no banco as linhas cujo e-mail coincide (sem diferenciar caixa) com o e-mail sondado e a conta-alvo;
  3. grava um marcador no log do PostgreSQL, faz o pedido, grava outro marcador;
  4. fotografa o banco de novo.
O SQL do servidor entre os marcadores é extraído depois por t3_sql.py.

Uso: python3 -I t3_probe.py <estado_seed.json> <saida.json> <pasta EMAIL_FILE_PATH>
Todos os e-mails são fictícios (domínios reservados .test).
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

import requests

BASE = 'http://127.0.0.1:8781/api/v1'
estado = json.load(open(sys.argv[1]))
SAIDA = sys.argv[2]
CREDS, IDS = estado['creds'], estado['ids']
SEED_EMAILS = {IDS[k]: v['email'] for k, v in CREDS.items()}
SEED_MAX_ID = max(SEED_EMAILS)
TENANT = {'shop_a': 'A', 'shop_b': 'B'}
MAIL_DIR = sys.argv[3]
SENHA_FORTE = 'Navalha-Fict-2026!'
SENHA_FRACA_VALIDADOR = '12345678'  # passa no min_length=8 do campo, cai nos validadores do Django (validate())
PAPEL_TENANT = {'admin_a': 'A', 'barbeiro_a': 'A', 'cliente_a1': 'A', 'cliente_a2': 'A', 'admin_b': 'B',
                'barbeiro_b': 'B', 'cliente_b': 'B', 'inativo_b': 'B', 'sem_barbearia': '(sem barbearia)',
                'superuser': '(plataforma)', None: '(anônimo)'}


def psql(sql):
    r = subprocess.run(['psql', '-X', '-w', '-A', '-t', '-F', '\t', '-h', '127.0.0.1', '-p', '55432', '-U', 'smoke',
                        '-d', 't3_db', '-q', '-c', sql], capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'})
    if r.returncode:
        raise SystemExit(f'psql falhou: {r.stderr}')
    return r.stdout.strip()


def lit(s):
    return "'" + s.replace("'", "''") + "'"


def restaurar():
    psql(f'delete from token_blacklist_blacklistedtoken where token_id in (select id from token_blacklist_outstandingtoken where user_id > {SEED_MAX_ID});'
         f' delete from token_blacklist_outstandingtoken where user_id > {SEED_MAX_ID};'
         f' delete from barbershops_barber where user_id > {SEED_MAX_ID};'
         f' delete from accounts_user where id > {SEED_MAX_ID};')
    for pk, email in SEED_EMAILS.items():
        psql(f'update accounts_user set email = {lit(email)} where id = {pk} and email <> {lit(email)}')


def foto(email, alvo_id):
    linhas = []
    if email:
        out = psql('select id, email, coalesce(barbershop_id::text, \'null\'), is_active from accounts_user '
                   f'where lower(email) = lower(btrim({lit(email)})) order by id')
        linhas += [dict(zip(['id', 'email', 'barbershop_id', 'is_active'], l.split('\t'))) for l in out.splitlines() if l]
    alvo = None
    if alvo_id:
        out = psql(f'select id, email, nome from accounts_user where id = {alvo_id}')
        alvo = dict(zip(['id', 'email', 'nome'], out.split('\t'))) if out else None
    total = int(psql('select count(*) from accounts_user'))
    return {'contas_com_o_email_sem_diferenciar_caixa': linhas, 'conta_alvo': alvo, 'total_de_usuarios': total}


def login(chave):
    c = CREDS[chave]
    r = requests.post(f'{BASE}/auth/login/', json={'email': c['email'], 'password': c['password']}, timeout=30)
    r.raise_for_status()
    return r.json()['access']


def ler_mensagem(caminho):
    texto = open(caminho, encoding='utf-8', errors='replace').read()
    para = re.findall(r'^To: (.*)$', texto, re.M)
    uids = re.findall(r'^uid: (\S+)$', texto, re.M)
    contas = []
    for u in uids:
        try:
            contas.append(int(base64.urlsafe_b64decode(u + '=' * (-len(u) % 4)).decode()))
        except Exception:
            contas.append(None)
    return {'para': para, 'uid_decodificado_id_da_conta': contas,
            'token': 'presente (removido)' if re.search(r'^token: ', texto, re.M) else 'ausente'}


def marcar(cid, fase):
    psql(f"select 'T3MARK {cid} {fase}'")


def redigir(texto):
    import re
    texto = re.sub(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', '<token removido>', texto)
    return texto


TOKENS = {}
CENARIOS = []


def cen(cid, grupo, descricao, papel, metodo, caminho, corpo, email_sondado, dono, esperado, alvo=None, preparo=None):
    CENARIOS.append(dict(id=cid, grupo=grupo, descricao=descricao, papel=papel, metodo=metodo, caminho=caminho,
                         corpo=corpo, email_sondado=email_sondado, dono_do_email=dono, esperado=esperado,
                         alvo=alvo, preparo=preparo))


def novo(cid):
    return f'novo.{cid.lower()}@exemplo.test'


E = {k: v['email'] for k, v in CREDS.items()}

# ---------------------------------------------------------------- cadastro público (anônimo)
R = 'POST /auth/register/ (cadastro público)'
cen('R01', R, 'e-mail nunca utilizado, senha válida', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': novo('R01'), 'password': SENHA_FORTE}, novo('R01'), 'novo', '201, conta criada')
cen('R02', R, 'e-mail de outra conta sem barbearia (mesmo "espaço" do cadastro público)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': E['sem_barbearia'], 'password': SENHA_FORTE}, E['sem_barbearia'], 'sem barbearia', '400')
cen('R03', R, 'e-mail de cliente da barbearia B', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': E['cliente_b'], 'password': SENHA_FORTE}, E['cliente_b'], 'B', '400')
cen('R04', R, 'e-mail de cliente de B + senha que falha nos validadores (sem efeito colateral)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': E['cliente_b'], 'password': SENHA_FRACA_VALIDADOR}, E['cliente_b'], 'B', '400 só em email')
cen('R05', R, 'e-mail nunca utilizado + a mesma senha fraca (par do R04)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': novo('R05'), 'password': SENHA_FRACA_VALIDADOR}, novo('R05'), 'novo', '400 só em password')
cen('R06', R, 'e-mail de cliente de B com maiúsculas na parte local (Cliente.B@...)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': 'Cliente.B@beta.test', 'password': SENHA_FORTE}, 'Cliente.B@beta.test', 'B (variação de caixa)', '?')
cen('R07', R, 'e-mail de cliente de B com maiúsculas no domínio (...@BETA.TEST)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': 'cliente.b@BETA.TEST', 'password': SENHA_FORTE}, 'cliente.b@BETA.TEST', 'B (variação de caixa)', '?')
cen('R08', R, 'e-mail nunca utilizado com maiúsculas no domínio (par do R07)', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': 'novo.r08@EXEMPLO.TEST', 'password': SENHA_FORTE}, 'novo.r08@EXEMPLO.TEST', 'novo', '201')
cen('R09', R, 'e-mail de cliente de B com espaços antes e depois', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': '  ' + E['cliente_b'] + '  ', 'password': SENHA_FORTE}, E['cliente_b'], 'B', '400')
cen('R10', R, 'e-mail de conta INATIVA de B', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': E['inativo_b'], 'password': SENHA_FORTE}, E['inativo_b'], 'B (inativa)', '400')
cen('R11', R, 'e-mail do superusuário da plataforma', None, 'POST', '/auth/register/',
    {'nome': 'Rita Nova', 'email': E['superuser'], 'password': SENHA_FORTE}, E['superuser'], 'plataforma', '400')

# ---------------------------------------------------------------- criação por administrador
C = 'POST /users/ (criação de usuário)'
cen('C01', C, 'admin A cria cliente com e-mail nunca utilizado', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': novo('C01'), 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, novo('C01'), 'novo', '201')
cen('C02', C, 'admin A cria cliente com e-mail de cliente A2 (mesma barbearia)', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_a2'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_a2'], 'A', '400')
cen('C03', C, 'admin A cria cliente com e-mail de cliente de B (outra barbearia)', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '400 (oráculo)')
cen('C04', C, 'admin A: e-mail de cliente de B + senha fraca (sem efeito colateral)', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FRACA_VALIDADOR, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '400 só em email')
cen('C05', C, 'admin A: e-mail nunca utilizado + a mesma senha fraca (par do C04)', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': novo('C05'), 'password': SENHA_FRACA_VALIDADOR, 'tipo_perfil': 'cliente'}, novo('C05'), 'novo', '400 só em password')
cen('C06', C, 'admin A cria barbeiro com e-mail de barbeiro de B', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['barbeiro_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'barbeiro', 'especialidade': 'Corte'},
    E['barbeiro_b'], 'B', '400')
cen('C07', C, 'admin A cria cliente com e-mail do admin de B', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['admin_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['admin_b'], 'B', '400')
cen('C08', C, 'admin A: e-mail de cliente de B com maiúsculas na parte local', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': 'Cliente.B@beta.test', 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, 'Cliente.B@beta.test', 'B (variação de caixa)', '?')
cen('C09', C, 'admin A: e-mail de cliente de B com maiúsculas no domínio', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': 'cliente.b@BETA.TEST', 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, 'cliente.b@BETA.TEST', 'B (variação de caixa)', '?')
cen('C10', C, 'admin A: e-mail de cliente de B com espaços', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': ' ' + E['cliente_b'] + ' ', 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '400')
cen('C11', C, 'admin A: e-mail de conta INATIVA de B', 'admin_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['inativo_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['inativo_b'], 'B (inativa)', '400')
cen('C12', C, 'cliente A1 tenta criar usuário com e-mail de B', 'cliente_a1', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '403 antes da validação')
cen('C13', C, 'barbeiro A tenta criar usuário com e-mail de B', 'barbeiro_a', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '403 antes da validação')
cen('C14', C, 'conta sem barbearia tenta criar usuário com e-mail de B', 'sem_barbearia', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '403 antes da validação')
cen('C15', C, 'superusuário (sem barbearia) cria com e-mail de B', 'superuser', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': E['cliente_b'], 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, E['cliente_b'], 'B', '400')
cen('C16', C, 'superusuário (sem barbearia) cria com e-mail nunca utilizado', 'superuser', 'POST', '/users/',
    {'nome': 'Caio Novo', 'email': novo('C16'), 'password': SENHA_FORTE, 'tipo_perfil': 'cliente'}, novo('C16'), 'novo', '400 barbershop')

# ---------------------------------------------------------------- edição
P = 'PATCH/PUT /users/{id}/ (edição)'
a1, a2, cb = IDS['cliente_a1'], IDS['cliente_a2'], IDS['cliente_b']
cen('P01', P, 'cliente A1 troca o próprio e-mail por um nunca utilizado', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': novo('P01')}, novo('P01'), 'novo', '200', alvo=a1)
cen('P02', P, 'cliente A1 reenvia o próprio e-mail', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_a1']}, E['cliente_a1'], 'próprio', '200 sem mudança', alvo=a1)
cen('P03', P, 'cliente A1 tenta usar o e-mail de cliente A2 (mesma barbearia)', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_a2']}, E['cliente_a2'], 'A', '400', alvo=a1)
cen('P04', P, 'cliente A1 tenta usar o e-mail de cliente de B (outra barbearia)', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '400 (oráculo para qualquer cliente)', alvo=a1)
cen('P05', P, 'cliente A1: e-mail de B + nome vazio (sem efeito colateral)', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_b'], 'nome': ''}, E['cliente_b'], 'B', '400 email+nome', alvo=a1)
cen('P06', P, 'cliente A1: e-mail nunca utilizado + nome vazio (par do P05)', 'cliente_a1', 'PATCH', f'/users/{a1}/',
    {'email': novo('P06'), 'nome': ''}, novo('P06'), 'novo', '400 só nome', alvo=a1)
cen('P07', P, 'barbeiro A tenta usar o e-mail de cliente de B na própria conta', 'barbeiro_a', 'PATCH', f'/users/{IDS["barbeiro_a"]}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '400', alvo=IDS['barbeiro_a'])
cen('P08', P, 'admin A tenta usar o e-mail do admin de B na própria conta', 'admin_a', 'PATCH', f'/users/{IDS["admin_a"]}/',
    {'email': E['admin_b']}, E['admin_b'], 'B', '400', alvo=IDS['admin_a'])
cen('P09', P, 'admin A dá ao cliente A1 um e-mail nunca utilizado', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': novo('P09')}, novo('P09'), 'novo', '200', alvo=a1)
cen('P10', P, 'admin A dá ao cliente A1 o e-mail do cliente A2 (mesma barbearia)', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_a2']}, E['cliente_a2'], 'A', '400', alvo=a1)
cen('P11', P, 'admin A dá ao cliente A1 o e-mail de cliente de B', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '400 (oráculo)', alvo=a1)
cen('P12', P, 'admin A reenvia o e-mail atual do cliente A1', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_a1']}, E['cliente_a1'], 'próprio', '200 sem mudança', alvo=a1)
cen('P13', P, 'admin A tenta editar o e-mail de um cliente de B', 'admin_a', 'PATCH', f'/users/{cb}/',
    {'email': novo('P13')}, novo('P13'), 'novo', '404', alvo=cb)
cen('P14', P, 'cliente A1 tenta editar o e-mail do cliente A2 (SEC-12: 403, não alterado)', 'cliente_a1', 'PATCH', f'/users/{a2}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '403 antes da validação', alvo=a2)
cen('P15', P, 'admin A: cliente A1 com e-mail de B em maiúsculas na parte local', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': 'Cliente.B@beta.test'}, 'Cliente.B@beta.test', 'B (variação de caixa)', '?', alvo=a1)
cen('P16', P, 'admin A: cliente A1 com e-mail de B em maiúsculas no domínio', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': 'cliente.b@BETA.TEST'}, 'cliente.b@BETA.TEST', 'B (variação de caixa)', '?', alvo=a1)
cen('P17', P, 'admin A: cliente A1 com e-mail de B com espaços', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': '  ' + E['cliente_b'] + '  '}, E['cliente_b'], 'B', '400', alvo=a1)
cen('P18', P, 'admin A: cliente A1 com e-mail de conta INATIVA de B', 'admin_a', 'PATCH', f'/users/{a1}/',
    {'email': E['inativo_b']}, E['inativo_b'], 'B (inativa)', '400', alvo=a1)
cen('P19', P, 'conta sem barbearia tenta trocar o próprio e-mail', 'sem_barbearia', 'PATCH', f'/users/{IDS["sem_barbearia"]}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '404 (queryset vazio)', alvo=IDS['sem_barbearia'])
cen('P20', P, 'superusuário dá ao cliente A1 o e-mail de cliente de B', 'superuser', 'PATCH', f'/users/{a1}/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '400', alvo=a1)
cen('P21', P, 'PUT: admin A envia o cadastro do cliente A1 com e-mail de B', 'admin_a', 'PUT', f'/users/{a1}/',
    {'email': E['cliente_b'], 'nome': 'Carlos Cliente A1', 'tipo_perfil': 'cliente', 'is_active': True}, E['cliente_b'], 'B', '400', alvo=a1)
cen('P22', P, 'PUT: admin A envia o cadastro do cliente A1 com e-mail nunca utilizado', 'admin_a', 'PUT', f'/users/{a1}/',
    {'email': novo('P22'), 'nome': 'Carlos Cliente A1', 'tipo_perfil': 'cliente', 'is_active': True}, novo('P22'), 'novo', '200', alvo=a1)

# ---------------------------------------------------------------- login e recuperação de senha (comparação)
L = 'login e recuperação de senha (comparação)'
cen('L01', L, 'login: e-mail existente (cliente de B), senha errada', None, 'POST', '/auth/login/',
    {'email': E['cliente_b'], 'password': 'Senha-Errada-123!'}, E['cliente_b'], 'B', '401')
cen('L02', L, 'login: e-mail nunca utilizado', None, 'POST', '/auth/login/',
    {'email': novo('L02'), 'password': 'Senha-Errada-123!'}, novo('L02'), 'novo', '401 igual ao L01')
cen('L03', L, 'login: conta inativa com a senha correta', None, 'POST', '/auth/login/',
    {'email': E['inativo_b'], 'password': CREDS['inativo_b']['password']}, E['inativo_b'], 'B (inativa)', '401 igual')
cen('L04', L, 'login: cliente A1 com a senha correta e maiúsculas na parte local', None, 'POST', '/auth/login/',
    {'email': 'Cliente.A1@alfa.test', 'password': CREDS['cliente_a1']['password']}, 'Cliente.A1@alfa.test', 'A (variação de caixa)', '?')
cen('L05', L, 'login: cliente A1 com a senha correta e maiúsculas no domínio', None, 'POST', '/auth/login/',
    {'email': 'cliente.a1@ALFA.TEST', 'password': CREDS['cliente_a1']['password']}, 'cliente.a1@ALFA.TEST', 'A (variação de caixa)', '?')
cen('L06', L, 'login: cliente A1 com a senha correta e espaços', None, 'POST', '/auth/login/',
    {'email': ' ' + E['cliente_a1'] + ' ', 'password': CREDS['cliente_a1']['password']}, E['cliente_a1'], 'A', '?')
cen('L07', L, 'recuperação: e-mail existente', None, 'POST', '/auth/password/reset/',
    {'email': E['cliente_b']}, E['cliente_b'], 'B', '204')
cen('L08', L, 'recuperação: e-mail nunca utilizado', None, 'POST', '/auth/password/reset/',
    {'email': novo('L08')}, novo('L08'), 'novo', '204 igual')
cen('L09', L, 'recuperação do cliente de B depois que um terceiro cadastrou "Cliente.B@beta.test" (nome "Aaron Variante")', None, 'POST',
    '/auth/password/reset/', {'email': E['cliente_b']}, E['cliente_b'], 'B + variação de caixa', '?',
    preparo={'metodo': 'POST', 'caminho': '/auth/register/',
             'corpo': {'nome': 'Aaron Variante', 'email': 'Cliente.B@beta.test', 'password': SENHA_FORTE}})


def main():
    restaurar()
    for chave in ('admin_a', 'barbeiro_a', 'cliente_a1', 'sem_barbearia', 'superuser'):
        TOKENS[chave] = login(chave)
    resultados = []
    for c in CENARIOS:
        restaurar()
        mails_antes = set(os.listdir(MAIL_DIR))
        preparo = None
        if c['preparo']:
            p = c['preparo']
            rp = requests.request(p['metodo'], BASE + p['caminho'], json=p['corpo'], timeout=30)
            preparo = {'pedido': f'{p["metodo"]} /api/v1{p["caminho"]}', 'corpo_enviado': {k: v for k, v in p['corpo'].items() if k != 'password'},
                       'status': rp.status_code, 'resposta': rp.text}
        antes = foto(c['email_sondado'], c['alvo'])
        headers = {'Accept': 'application/json'}
        if c['papel']:
            headers['Authorization'] = 'Bearer ' + TOKENS[c['papel']]
        marcar(c['id'], 'inicio')
        t0 = time.perf_counter()
        r = requests.request(c['metodo'], BASE + c['caminho'], json=c['corpo'], headers=headers, timeout=60)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        marcar(c['id'], 'fim')
        depois = foto(c['email_sondado'], c['alvo'])
        time.sleep(0.2)
        mensagens = [ler_mensagem(os.path.join(MAIL_DIR, f)) for f in sorted(set(os.listdir(MAIL_DIR)) - mails_antes)]
        try:
            corpo_json = r.json()
        except ValueError:
            corpo_json = None
        enviado = {k: ('<senha omitida>' if k == 'password' else v) for k, v in c['corpo'].items()}
        resultados.append({
            'id': c['id'], 'grupo': c['grupo'], 'descricao': c['descricao'],
            'pedido': f'{c["metodo"]} /api/v1{c["caminho"]}',
            'papel': c['papel'] or 'anônimo', 'tenant_do_solicitante': PAPEL_TENANT[c['papel']],
            'email_sondado': c['email_sondado'], 'dono_do_email': c['dono_do_email'], 'esperado_registrado_antes': c['esperado'],
            'corpo_enviado': enviado, 'preparo': preparo,
            'status': r.status_code, 'content_type': r.headers.get('Content-Type'), 'resposta_integral': redigir(r.text),
            'resposta_json': json.loads(redigir(json.dumps(corpo_json))) if corpo_json is not None else None,
            'tempo_ms': ms, 'banco_antes': antes, 'banco_depois': depois,
            'usuarios_criados': depois['total_de_usuarios'] - antes['total_de_usuarios'],
            'mensagens_de_email_geradas': mensagens,
            'conta_alvo_alterada': (antes['conta_alvo'] != depois['conta_alvo']) if c['alvo'] else None,
        })
        print(f'{c["id"]:4} {r.status_code} {ms:7.1f} ms  {redigir(r.text)[:150]}')
    restaurar()
    json.dump(resultados, open(SAIDA, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
