"""
Sondagem da API isolada da auditoria (http://127.0.0.1:8765, banco descartável).
Não imprime tokens, senhas nem chaves: só códigos HTTP, campos e contagens.
Uso: python probe.py <state.json> <saida.json>
"""
import base64
import json
import sys
import time as _time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import requests

API = 'http://127.0.0.1:8765/api/v1'
state = json.load(open(sys.argv[1]))
CREDS, IDS = state['creds'], state['ids']
results = []


def rec(group, cid, desc, expected, actual, ok, note=''):
    results.append({'grupo': group, 'id': cid, 'verificacao': desc, 'esperado': expected,
                    'obtido': actual, 'ok': bool(ok), 'obs': note})


class S:
    def __init__(self, email):
        self.email = email
        self.s = requests.Session()
        r = self.s.post(f'{API}/auth/login/', json={'email': email, 'password': CREDS[email]})
        self.login_status = r.status_code
        self.login_body_keys = sorted(r.json().keys()) if r.ok else []
        self.access = r.json().get('access') if r.ok else None
        self.set_cookie = r.headers.get('Set-Cookie', '')

    def h(self):
        return {'Authorization': f'Bearer {self.access}'} if self.access else {}

    def get(self, path, **kw):
        return self.s.get(API + path, headers=self.h(), **kw)

    def post(self, path, data=None, **kw):
        # Contrato atual: o campo `cliente` é obrigatório no POST mesmo para o
        # próprio cliente (o frontend envia user.id). Repetimos o comportamento.
        if path == '/appointments/' and isinstance(data, dict) and 'cliente' not in data and self.access:
            if not hasattr(self, '_me'):
                self._me = self.s.get(API + '/users/me/', headers=self.h()).json()
            if self._me.get('tipo_perfil') == 'cliente':
                data = {**data, 'cliente': self._me['id']}
        return self.s.post(API + path, json=data, headers=self.h(), **kw)

    def patch(self, path, data=None, **kw):
        return self.s.patch(API + path, json=data, headers=self.h(), **kw)

    def delete(self, path, **kw):
        return self.s.delete(API + path, headers=self.h(), **kw)


def body(r):
    try:
        return r.json()
    except Exception:
        return r.text[:200]


def short(r):
    b = body(r)
    if isinstance(b, dict):
        return {k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 220 else '…') for k, v in b.items()
                if k not in ('access', 'refresh')}
    return b


today = date.today()


def next_weekday(wd, min_days=2):
    d = today + timedelta(days=min_days)
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


def iso(d, hh, mm=0):
    # America/Sao_Paulo, UTC-3 sem horário de verão.
    return f'{d.isoformat()}T{hh:02d}:{mm:02d}:00-03:00'


admin = S('admin.a@exemplo.test')
admin_b = S('admin.b@exemplo.test')
cli1 = S('cliente1@exemplo.test')
cli2 = S('cliente2@exemplo.test')
barb1 = S('joao.barbeiro@exemplo.test')
sup = S('plataforma@exemplo.test')
for who in (admin, admin_b, cli1, cli2, barb1, sup):
    assert who.login_status == 200, (who.email, who.login_status)

B1, B2, B3 = IDS['barbers']
SV_CORTE, SV_BARBA, SV_COMBO, SV_PIG = IDS['services']
appt_b = admin_b.get('/appointments/').json()['results'][0]['id']

# Datas livres: escolhe um dia útil distante (sem agendamentos semeados).
FREE_DAY = today + timedelta(days=12)
while FREE_DAY.weekday() == 6:
    FREE_DAY += timedelta(days=1)

# ----------------------------------------------------------------- Isolamento
G = 'Isolamento entre barbearias'
checks = [
    ('ISO-01', 'admin A lê barbearia B', admin.get(f"/barbershops/{IDS['shop_b']}/"), 404),
    ('ISO-02', 'admin A altera barbearia B', admin.patch(f"/barbershops/{IDS['shop_b']}/", {'nome': 'x'}), 404),
    ('ISO-03', 'admin A lê admin B', admin.get(f"/users/{IDS['admin_b']}/"), 404),
    ('ISO-04', 'admin A altera cliente B', admin.patch(f"/users/{IDS['cliente_b']}/", {'nome': 'x'}), 404),
    ('ISO-05', 'admin A desativa cliente B', admin.delete(f"/users/{IDS['cliente_b']}/"), 404),
    ('ISO-06', 'admin A lê serviço B', admin.get(f"/services/{IDS['service_b']}/"), 404),
    ('ISO-07', 'admin A altera serviço B', admin.patch(f"/services/{IDS['service_b']}/", {'preco': '1.00'}), 404),
    ('ISO-08', 'admin A lê barbeiro B', admin.get(f"/barbers/{IDS['barber_b']}/"), 404),
    ('ISO-09', 'admin A lê agendamento B', admin.get(f'/appointments/{appt_b}/'), 404),
    ('ISO-10', 'admin A altera agendamento B', admin.patch(f'/appointments/{appt_b}/', {'observacoes': 'x'}), 404),
    ('ISO-11', 'admin A cancela agendamento B', admin.delete(f'/appointments/{appt_b}/'), 404),
    ('ISO-12', 'admin A agenda com barbeiro B', admin.post('/appointments/', {
        'cliente': IDS['clientes'][0], 'barbeiro': IDS['barber_b'], 'servico': SV_CORTE,
        'data_hora': iso(FREE_DAY, 10)}), 400),
    ('ISO-13', 'admin A agenda serviço B', admin.post('/appointments/', {
        'cliente': IDS['clientes'][0], 'barbeiro': B1, 'servico': IDS['service_b'],
        'data_hora': iso(FREE_DAY, 10)}), 400),
    ('ISO-14', 'admin A agenda cliente B', admin.post('/appointments/', {
        'cliente': IDS['cliente_b'], 'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 10)}), 400),
    ('ISO-15', 'admin A promove cliente B a barbeiro', admin.post('/barbers/', {
        'user': IDS['cliente_b'], 'especialidade': 'x'}), 400),
    ('ISO-16', 'horários livres de barbeiro B', admin.get('/appointments/available-slots/', params={
        'barbeiro': IDS['barber_b'], 'servico': SV_CORTE, 'data': FREE_DAY.isoformat()}), 404),
    ('ISO-17', 'exclude_appointment_id de B', cli1.get('/appointments/available-slots/', params={
        'barbeiro': B1, 'servico': SV_CORTE, 'data': FREE_DAY.isoformat(), 'exclude_appointment_id': appt_b}), 404),
    ('ISO-18', 'cliente A lê agendamento de B', cli1.get(f'/appointments/{appt_b}/'), 404),
]
for cid, desc, r, exp in checks:
    rec(G, cid, desc, exp, r.status_code, r.status_code == exp, json.dumps(short(r), ensure_ascii=False)[:180])

rr = admin.get('/appointments/revenue-report/', params={'barbeiro': IDS['barber_b'], 'start': (today - timedelta(days=60)).isoformat()})
rec(G, 'ISO-19', 'revenue-report filtrando barbeiro de B', '200 com total 0', f"{rr.status_code} total={body(rr).get('total_revenue')}",
    rr.status_code == 200 and body(rr).get('total_revenue') == '0.00')
leak = []
for path, key in (('/users/', 'barbershop'), ('/services/', 'barbershop'), ('/barbers/', 'barbershop'), ('/appointments/', 'barbershop')):
    data = admin.get(path).json()['results']
    leak += [path for item in data if item.get(key) != IDS['shop_a']]
rec(G, 'ISO-20', 'listas do admin A só têm registros de A', 'nenhum registro de B', f'{len(leak)} registros de outra barbearia', not leak)
other = cli2.get('/appointments/').json()['results'][0]['id']
r = cli1.get(f'/appointments/{other}/')
rec(G, 'ISO-21', 'cliente lê agendamento de outro cliente da mesma barbearia', 404, r.status_code, r.status_code == 404)

# Oráculo de existência de IDs de outra barbearia
r_other = admin.post('/appointments/', {'cliente': IDS['clientes'][0], 'barbeiro': IDS['barber_b'], 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 10)})
r_none = admin.post('/appointments/', {'cliente': IDS['clientes'][0], 'barbeiro': 999999, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 10)})
m1, m2 = json.dumps(body(r_other), ensure_ascii=False), json.dumps(body(r_none), ensure_ascii=False)
rec(G, 'ISO-22', 'mensagem para ID de outra barbearia x ID inexistente', 'mensagens iguais', f'outra={m1[:90]} | inexistente={m2[:90]}', m1 == m2,
    'Mensagens diferentes revelam que o ID existe em outra barbearia')
r_x = cli1.get('/appointments/available-slots/', params={'barbeiro': B1, 'servico': SV_CORTE, 'data': FREE_DAY.isoformat(), 'exclude_appointment_id': 999999})
rec(G, 'ISO-23', 'exclude_appointment_id: outra barbearia x inexistente', 'mensagens iguais',
    f"outra={body(checks[16][2]).get('detail')} | inexistente={body(r_x).get('detail')}", body(checks[16][2]) == body(r_x))

# ------------------------------------------------------------------ Perfis
G = 'Perfis e permissões'
def chk(cid, desc, r, exp, note=''):
    ok = r.status_code in (exp if isinstance(exp, tuple) else (exp,))
    rec(G, cid, desc, exp, r.status_code, ok, note or json.dumps(short(r), ensure_ascii=False)[:160])

chk('PER-01', 'cliente lista usuários', cli1.get('/users/'), 403)
chk('PER-02', 'cliente cria usuário', cli1.post('/users/', {'email': 'x@exemplo.test', 'nome': 'X', 'password': 'Senha-forte-987', 'tipo_perfil': 'cliente'}), 403)
r = cli1.patch(f"/users/{IDS['clientes'][0]}/", {'tipo_perfil': 'admin', 'is_active': False})
rec(G, 'PER-03', 'cliente tenta se promover e se desativar', 'perfil e status inalterados',
    f"{r.status_code} tipo={body(r).get('tipo_perfil')} ativo={body(r).get('is_active')}",
    body(r).get('tipo_perfil') == 'cliente' and body(r).get('is_active') is True)
chk('PER-04', 'cliente cria serviço', cli1.post('/services/', {'nome': 'X', 'preco': '1.00', 'duracao': 30}), 403)
chk('PER-05', 'cliente altera serviço', cli1.patch(f'/services/{SV_CORTE}/', {'preco': '1.00'}), 403)
chk('PER-06', 'cliente cria barbeiro', cli1.post('/barbers/', {'user': IDS['clientes'][1], 'especialidade': 'x'}), 403)
chk('PER-07', 'cliente altera barbearia', cli1.patch(f"/barbershops/{IDS['shop_a']}/", {'nome': 'x'}), 403)
chk('PER-08', 'cliente consulta faturamento (SEC-02)', cli1.get('/appointments/revenue-report/'), 403)
chk('PER-09', 'barbeiro consulta faturamento (SEC-02)', barb1.get('/appointments/revenue-report/'), 403)
chk('PER-10', 'barbeiro consulta faturamento filtrando o próprio id', barb1.get('/appointments/revenue-report/', params={'barbeiro': B1}), 403)
chk('PER-11', 'admin consulta faturamento', admin.get('/appointments/revenue-report/'), 200)
bl = cli1.get('/barbers/').json()['results']
rec(G, 'PER-12', 'cliente recebe e-mail de login dos barbeiros (SEC-03)', 'sem campo email',
    f"{sum(1 for b in bl if b.get('email'))} de {len(bl)} itens com e-mail", not any(b.get('email') for b in bl))
r = cli1.get(f"/users/{IDS['clientes'][1]}/")
rec(G, 'PER-13', 'cliente consulta outro cliente por id', '404 (não revelar existência)', r.status_code, r.status_code == 404,
    '403 confirma que o id existe no tenant')
chk('PER-14', 'barbeiro lista usuários', barb1.get('/users/'), 403)
chk('PER-15', 'barbeiro cria serviço', barb1.post('/services/', {'nome': 'X', 'preco': '1.00', 'duracao': 30}), 403)
lst = barb1.get('/appointments/', params={'page': 1}).json()
own = all(a['barbeiro'] == B1 for a in lst['results'])
rec(G, 'PER-16', 'barbeiro vê só a própria agenda', 'só barbeiro próprio', f"{lst['count']} itens; todos próprios={own}", own)
other_barber_appt = admin.get('/appointments/', params={'barbeiro': B2}).json()['results'][0]['id']
chk('PER-17', 'barbeiro altera agendamento de outro barbeiro', barb1.patch(f'/appointments/{other_barber_appt}/', {'observacoes': 'x'}), 404)
chk('PER-18', 'superusuário cria serviço sem contexto de barbearia', sup.post('/services/', {'nome': 'X', 'preco': '1.00', 'duracao': 30}), 403)
sc = sup.get('/appointments/').json()['count']
rec(G, 'PER-19', 'superusuário lê agendamentos de todas as barbearias', 'todas', f'{sc} agendamentos', sc > 400)

# Cliente cria agendamento já com status "confirmado"
r = cli1.post('/appointments/', {'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 9), 'status': 'confirmado'})
rec('Regras de negócio', 'NEW-STATUS', 'cliente cria agendamento enviando status=confirmado', '400/403 ou status agendado',
    f"{r.status_code} status={body(r).get('status')}", not (r.status_code == 201 and body(r).get('status') == 'confirmado'))
self_confirmed = body(r).get('id')
r = barb1.post('/appointments/', {'cliente': IDS['clientes'][2], 'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 9, 30), 'status': 'cancelado'})
rec('Regras de negócio', 'NEW-STATUS-2', 'barbeiro cria agendamento já cancelado', 'status inicial agendado', f"{r.status_code} status={body(r).get('status')}",
    body(r).get('status') in (None, 'agendado'))
r = cli1.post('/appointments/', {'cliente': IDS['clientes'][1], 'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 10)})
rec(G, 'PER-20', 'cliente tenta agendar em nome de outro cliente', 'gravado para o próprio cliente',
    f"{r.status_code} cliente={body(r).get('cliente')}", body(r).get('cliente') == IDS['clientes'][0])
own_appt = body(r).get('id')
chk('PER-21', 'cliente confirma o próprio agendamento', cli1.patch(f'/appointments/{own_appt}/', {'status': 'confirmado'}), 403)
chk('PER-22', 'cliente altera agendamento de outro cliente', cli1.patch(f'/appointments/{other}/', {'observacoes': 'x'}), 404)

# Barbeiro: DELETE x PATCH cancelado; troca de cliente
r = barb1.post('/appointments/', {'cliente': IDS['clientes'][2], 'barbeiro': B2, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 11)})
rec(G, 'PER-23', 'barbeiro agenda informando outro barbeiro', 'gravado no próprio barbeiro', f"{r.status_code} barbeiro={body(r).get('barbeiro')}",
    body(r).get('barbeiro') == B1)
bappt = body(r).get('id')
r_del = barb1.delete(f'/appointments/{bappt}/')
r_cli = barb1.patch(f'/appointments/{bappt}/', {'cliente': IDS['clientes'][3]})
r_can = barb1.patch(f'/appointments/{bappt}/', {'status': 'cancelado'})
rec('Regras de negócio', 'BUS-12', 'barbeiro: DELETE x PATCH cancelado x troca de cliente', 'mesma regra nos dois caminhos',
    f'DELETE={r_del.status_code}; PATCH cliente={r_cli.status_code}; PATCH cancelado={r_can.status_code}',
    not (r_del.status_code == 403 and r_can.status_code == 200))

# ------------------------------------------------------------ Regras de negócio
G = 'Regras de negócio'
# BUS-01
me = admin.get('/users/me/').json()['id']
r1 = admin.patch(f'/users/{me}/', {'tipo_perfil': 'cliente'})
r2 = admin.delete(f'/users/{me}/')
rec(G, 'BUS-01', 'admin se rebaixa / se desativa', '400 nos dois', f'PATCH={r1.status_code} DELETE={r2.status_code}',
    r1.status_code == 400 and r2.status_code == 400, json.dumps(body(r1), ensure_ascii=False)[:150])
r = sup.patch(f'/users/{me}/', {'is_active': False})
rec(G, 'BUS-01b', 'superusuário desativa o único admin da barbearia', 400, r.status_code, r.status_code == 400)

# BUS-03
r = cli1.post('/appointments/', {'barbeiro': B2, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 12)})
a3 = body(r)['id']
admin.patch(f'/appointments/{a3}/', {'status': 'confirmado'})
r = cli1.patch(f'/appointments/{a3}/', {'data_hora': iso(FREE_DAY, 13)})
rec(G, 'BUS-03', 'cliente reagenda horário confirmado', 'status volta a agendado', f"{r.status_code} status={body(r).get('status')}",
    body(r).get('status') == 'agendado')

# BUS-04
r = cli1.post('/appointments/', {'barbeiro': B3, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 18, 30)})
a4 = body(r).get('id')
r = admin.patch(f'/appointments/{a4}/', {'servico': SV_COMBO})
rec(G, 'BUS-04', 'troca 30→60 min às 18:30 (fecha 19:00)', 400, r.status_code, r.status_code == 400)

# BUS-05
r = admin.patch(f"/barbershops/{IDS['shop_a']}/", {'horario_abertura': '18:00:00', 'horario_fechamento': '08:00:00'})
r2 = admin.patch(f"/barbershops/{IDS['shop_a']}/", {'horario_fechamento': '08:30:00'})
rec(G, 'BUS-05', 'fechamento antes da abertura (completo e parcial)', '400 nos dois', f'completo={r.status_code} parcial={r2.status_code}',
    r.status_code == 400 and r2.status_code == 400)
admin.patch(f"/barbershops/{IDS['shop_a']}/", {'horario_abertura': '09:00:00', 'horario_fechamento': '19:00:00'})

# BUS-06 / BUS-11 / BUS-10
sunday = next_weekday(6)
r = cli1.get('/appointments/available-slots/', params={'barbeiro': B1, 'servico': SV_COMBO, 'data': sunday.isoformat()})
rec(G, 'BUS-06', f'horários num domingo ({sunday.isoformat()})', 'lista vazia', f"{len(body(r).get('slots', []))} horários", not body(r).get('slots'))
slots60 = body(r).get('slots', [])
rec(G, 'BUS-11', 'passo dos horários de serviço de 60 min', 'passo menor que a duração', ', '.join(slots60[:6]),
    any(s.endswith(':30') for s in slots60))
r = cli1.get('/appointments/available-slots/', params={'barbeiro': B1, 'servico': SV_CORTE, 'data': (today - timedelta(days=1)).isoformat()})
rec(G, 'BUS-10', 'horários para ontem', 'lista vazia ou 400', f"{r.status_code} {len(body(r).get('slots', []))} horários",
    r.status_code == 400 or not body(r).get('slots'))

# BUS-07
r = cli1.post('/appointments/', {'barbeiro': B2, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 15)})
a7 = body(r)['id']
admin.patch(f'/appointments/{a7}/', {'status': 'confirmado'})
r = admin.patch(f'/appointments/{a7}/', {'status': 'realizado'})
rec(G, 'BUS-07', 'marcar realizado um horário futuro', 400, r.status_code, r.status_code == 400, json.dumps(body(r), ensure_ascii=False)[:150])

# AUTH-02
anon = requests.Session()
r = anon.post(f'{API}/auth/register/', json={'email': 'CLIENTE1@exemplo.test', 'nome': 'Duplicado', 'password': 'Senha-forte-987'})
rec(G, 'AUTH-02', 'cadastro de e-mail existente com maiúsculas', 400, r.status_code, r.status_code == 400)
r = anon.post(f'{API}/auth/login/', json={'email': 'Cliente1@Exemplo.test', 'password': CREDS['cliente1@exemplo.test']})
rec(G, 'AUTH-02b', 'login com outra capitalização do e-mail', 200, r.status_code, r.status_code == 200)
# PROD-01
r = anon.post(f'{API}/auth/register/', json={'email': 'novo.cliente@exemplo.test', 'nome': 'Novo', 'password': 'Senha-forte-987'})
rec(G, 'PROD-01', 'cadastro público cria conta vinculada a barbearia', 'vínculo com barbearia', f"{r.status_code} barbershop={body(r).get('barbershop')} tipo={body(r).get('tipo_perfil')}",
    body(r).get('barbershop') is not None)

# Novos: sobreposição do próprio cliente, cancelamento retroativo
r1 = cli1.post('/appointments/', {'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 16)})
r2 = cli1.post('/appointments/', {'barbeiro': B2, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 16)})
rec(G, 'NEW-OVERLAP', 'mesmo cliente com dois horários simultâneos (barbeiros diferentes)', 'segundo recusado',
    f'{r1.status_code} / {r2.status_code}', r2.status_code != 201)
past = [a for a in cli1.get('/appointments/', params={'status': 'agendado'}).json()['results']
        if a['data_hora'] < datetime.now().astimezone().isoformat()]
if past:
    r = cli1.delete(f"/appointments/{past[0]['id']}/")
    rec(G, 'NEW-PASTCANCEL', 'cliente cancela horário que já passou', 'recusado', f"{r.status_code} (data {past[0]['data_hora'][:16]})", r.status_code != 204)
past_conf = [a for a in admin.get('/appointments/', params={'status': 'confirmado'}).json()['results']
             if a['data_hora'] < datetime.now().astimezone().isoformat()]
cnt = 0
for p in range(1, 30):
    page = admin.get('/appointments/', params={'status': 'agendado', 'page': p})
    if page.status_code != 200:
        break
    cnt += sum(1 for a in page.json()['results'] if a['data_hora'] < datetime.now().astimezone().isoformat())
    if not page.json()['next']:
        break
rec(G, 'BUS-08', 'horários vencidos ainda "agendado" (sem desfecho)', 'status próprio ou sinalização', f'{cnt} vencidos como agendado', cnt == 0)

# BUS-13: desativar barbeiro com horários futuros
fut_before = admin.get('/appointments/', params={'barbeiro': B3}).json()['results']
fut_ids = [a['id'] for a in fut_before if a['status'] in ('agendado', 'confirmado') and a['data_hora'] > datetime.now().astimezone().isoformat()]
r = admin.delete(f'/barbers/{B3}/')
still = [a for a in admin.get('/appointments/', params={'barbeiro': B3}).json()['results'] if a['id'] in fut_ids and a['status'] in ('agendado', 'confirmado')]
rec(G, 'BUS-13', 'desativar barbeiro com horários futuros', 'decisão sobre os horários', f'DELETE={r.status_code}; {len(still)} de {len(fut_ids)} horários futuros continuam ativos',
    not still)

# API-01
r = admin.get('/appointments/', params={'page_size': 100})
rec(G, 'API-01', 'page_size=100', '100 itens', f"{len(body(r)['results'])} itens", len(body(r)['results']) == 100)
r_all = admin.get('/users/').json()['count']
r_s = admin.get('/users/', params={'search': 'Bruno'}).json()['count']
r_t = admin.get('/users/', params={'tipo_perfil': 'cliente'}).json()['count']
rec(G, 'API-01b', 'busca e filtro de perfil em /users/', 'resultado filtrado', f'total={r_all} search={r_s} tipo_perfil={r_t}', r_s < r_all and r_t < r_all)
r1 = admin.get('/appointments/', params={'ordering': 'data_hora'}).json()['results'][0]['data_hora']
r2 = admin.get('/appointments/').json()['results'][0]['data_hora']
rec(G, 'API-01c', 'ordering=data_hora', 'ordem crescente', f'primeiro={r1[:16]} padrão={r2[:16]}', r1 != r2)

# API-02: dia em UTC no relatório
y = (today - timedelta(days=1)).isoformat()
r = admin.get('/appointments/revenue-report/', params={'start': y, 'end': y})
daily = body(r).get('daily', [])
rec(G, 'API-02', f'atendimento realizado ontem às 22:30 no faturamento diário (start=end={y})', f'dia {y}',
    json.dumps(daily, ensure_ascii=False)[:200], all(d['date'] == y for d in daily) and daily)

# BUS-02: desativação/suspensão
G2 = 'Barbearia desativada'
r = sup.delete(f"/barbershops/{IDS['shop_a']}/", params={'confirmar': 'Barbearia Navalha Fictícia'})
rec(G2, 'BUS-02a', 'plataforma desativa a barbearia A (DELETE com confirmação)', 204, r.status_code, r.status_code == 204)
r = S('cliente3@exemplo.test')
rec(G2, 'BUS-02b', 'cliente da barbearia desativada faz login', 'decisão do produto', r.login_status, True, 'informativo')
cli3 = r
r = cli3.post('/appointments/', {'barbeiro': B1, 'servico': SV_CORTE, 'data_hora': iso(FREE_DAY, 17)})
rec(G2, 'BUS-02c', 'cliente agenda em barbearia desativada', 400, r.status_code, r.status_code == 400)
r = admin.post('/services/', {'nome': 'Serviço criado com a barbearia desativada', 'preco': '10.00', 'duracao': 30})
rec(G2, 'BUS-02d', 'admin cria serviço com a barbearia desativada', 'bloqueado', r.status_code, r.status_code != 201)
r = admin.post('/users/', {'email': 'novo.durante.suspensao@exemplo.test', 'nome': 'Novo', 'password': 'Senha-forte-987', 'tipo_perfil': 'cliente'})
rec(G2, 'BUS-02e', 'admin cadastra cliente com a barbearia desativada', 'bloqueado', r.status_code, r.status_code != 201)
r = admin.patch(f"/barbershops/{IDS['shop_a']}/", {'ativo': True})
rec(G2, 'BUS-02f', 'admin do tenant reativa a barbearia que a plataforma desativou', 403, f"{r.status_code} ativo={body(r).get('ativo')}",
    r.status_code == 403)
admin.patch(f"/barbershops/{IDS['shop_a']}/", {'ativo': True})
sup.patch(f"/barbershops/{IDS['shop_a']}/", {'ativo': True})

# ------------------------------------------------------------------ Sessão
G = 'Sessão e segurança HTTP'
c = admin.set_cookie
rec(G, 'SES-01', 'login devolve só access no corpo', "['access']", str(admin.login_body_keys), admin.login_body_keys == ['access'])
flags = {f: (f.lower() in c.lower()) for f in ('HttpOnly', 'SameSite=Lax', 'Path=/api/v1/auth/', 'Secure')}
rec(G, 'SES-02', 'flags do cookie de refresh (DEBUG=True)', 'HttpOnly, SameSite=Lax, Path restrito', json.dumps(flags), flags['HttpOnly'] and flags['SameSite=Lax'])
payload = json.loads(base64.urlsafe_b64decode(admin.access.split('.')[1] + '=='))
rec(G, 'SES-03', 'claims do access token', 'sem dado sensível', sorted(payload.keys()), True,
    f"exp-iat={payload['exp'] - payload['iat']}s; contém nome do usuário")
t = S('cliente4@exemplo.test')
old_cookie = t.s.cookies.get('barbearia_refresh')
r1 = t.s.post(f'{API}/auth/refresh/')
r2 = requests.post(f'{API}/auth/refresh/', cookies={'barbearia_refresh': old_cookie})
rec(G, 'SES-04', 'refresh por cookie e reuso do refresh antigo', '200 e depois 401', f'{r1.status_code} / {r2.status_code}', r1.status_code == 200 and r2.status_code == 401)
t.access = r1.json()['access']
r = t.post('/auth/logout/')
r2 = t.s.post(f'{API}/auth/refresh/')
rec(G, 'SES-05', 'logout e refresh posterior', '204 e 401', f'{r.status_code} / {r2.status_code}', r.status_code == 204 and r2.status_code == 401)
t = S('cliente5@exemplo.test')
r = admin.delete(f"/users/{IDS['clientes'][4]}/")
r2 = t.get('/users/me/')
rec(G, 'SES-06', 'access de usuário desativado', '401 imediato', f'desativação={r.status_code}; me={r2.status_code}', r2.status_code == 401)
r = requests.options(f'{API}/services/', headers={'Origin': 'http://malicioso.exemplo', 'Access-Control-Request-Method': 'GET'})
rec(G, 'SES-07', 'CORS de origem não autorizada', 'sem Access-Control-Allow-Origin', r.headers.get('Access-Control-Allow-Origin'), not r.headers.get('Access-Control-Allow-Origin'))
r = requests.options(f'{API}/services/', headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'GET'})
rec(G, 'SES-08', 'CORS aceita http://localhost:3000 (do .env)', 'só a origem do frontend', r.headers.get('Access-Control-Allow-Origin'), True,
    'informativo: origem extra na lista local')
r = admin.get('/services/')
hdrs = {k: r.headers.get(k) for k in ('X-Frame-Options', 'X-Content-Type-Options', 'Referrer-Policy', 'Cross-Origin-Opener-Policy', 'Content-Security-Policy')}
rec(G, 'SES-09', 'cabeçalhos de segurança', 'CSP presente', json.dumps(hdrs), bool(hdrs['Content-Security-Policy']))
t0 = _time.perf_counter(); r1 = anon.post(f'{API}/auth/password/reset/', json={'email': 'cliente6@exemplo.test'}); t1 = _time.perf_counter()
r2 = anon.post(f'{API}/auth/password/reset/', json={'email': 'naoexiste@exemplo.test'}); t2 = _time.perf_counter()
rec(G, 'SES-10', 'recuperação de senha: existente x inexistente', 'mesma resposta', f'{r1.status_code} ({(t1-t0)*1000:.0f} ms) / {r2.status_code} ({(t2-t1)*1000:.0f} ms)', r1.status_code == r2.status_code)
r = anon.post(f'{API}/auth/password/reset/confirm/', json={'uid': 'MQ', 'token': 'invalido', 'new_password': 'Senha-forte-987'})
rec(G, 'SES-11', 'confirmação com token inválido', 400, r.status_code, r.status_code == 400)
r = requests.get('http://127.0.0.1:8765/api/v1/rota-inexistente/')
rec(G, 'SES-12', '404 com DEBUG=True do .env', 'sem página técnica', f"{r.status_code} {'Django tried these URL patterns' in r.text and 'página de debug com lista de rotas' or r.headers.get('Content-Type')}",
    'URL patterns' not in r.text, 'só relevante se o .env de desenvolvimento for para produção')
r = cli1.post('/appointments/', {'barbeiro': 'abc', 'servico': SV_CORTE, 'data_hora': 'ontem'})
rec(G, 'SES-13', 'entrada malformada em agendamento', 400, r.status_code, r.status_code == 400)
r = cli1.get('/appointments/available-slots/', params={'barbeiro': B1, 'servico': SV_CORTE, 'data': FREE_DAY.isoformat(), 'exclude_appointment_id': 'abc'})
rec(G, 'SES-14', 'exclude_appointment_id não numérico', '400/404 sem 500', r.status_code, r.status_code in (400, 404))
r = admin.get('/appointments/revenue-report/', params={'start': '2026-13-01'})
rec(G, 'SES-15', 'data inválida no relatório', 400, r.status_code, r.status_code == 400)

# ------------------------------------------------------------- Concorrência
G = 'Concorrência (PostgreSQL 16)'
slot = iso(FREE_DAY + timedelta(days=1), 10)
clients = [S(f'cliente{i}@exemplo.test') for i in (1, 2, 3, 4, 6)] * 4
def book(sess):
    return sess.post('/appointments/', {'barbeiro': B2, 'servico': SV_CORTE, 'data_hora': slot}).status_code
with ThreadPoolExecutor(max_workers=20) as ex:
    codes = list(ex.map(book, clients))
rec(G, 'CON-01', '20 pedidos simultâneos para o mesmo horário e barbeiro', 'exatamente 1 criado', json.dumps({c: codes.count(c) for c in set(codes)}), codes.count(201) == 1)

json.dump(results, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
ok = sum(r['ok'] for r in results)
print(f'{len(results)} verificações; {ok} conforme esperado; {len(results) - ok} divergentes')
for r in results:
    if not r['ok']:
        print(' X', r['id'], '-', r['verificacao'], '| obtido:', str(r['obtido'])[:140])
