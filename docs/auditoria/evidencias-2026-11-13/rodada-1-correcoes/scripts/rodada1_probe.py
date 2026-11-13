"""
Sondagem HTTP da 1ª rodada de correções (API isolada, banco descartável).
BUS-15, BUS-03, BUS-06, BUS-05, BUS-04 pelos três perfis. Sem tokens nem senhas na saída.
Uso: python rodada1_probe.py <state.json> <saida.json>
"""
import json
import sys
from datetime import date, timedelta

import requests

API = 'http://127.0.0.1:8765/api/v1'
state = json.load(open(sys.argv[1]))
CREDS, IDS = state['creds'], state['ids']
out = []


def rec(cid, desc, esperado, obtido, ok):
    out.append({'id': cid, 'verificacao': desc, 'esperado': esperado, 'obtido': obtido, 'ok': bool(ok)})


def login(email):
    s = requests.Session()
    s.headers['Authorization'] = 'Bearer ' + s.post(f'{API}/auth/login/', json={'email': email, 'password': CREDS[email]}).json()['access']
    s.me = s.get(f'{API}/users/me/').json()
    return s


def b(r):
    try:
        return r.json()
    except Exception:
        return r.text[:120]


def proximo(iso, minimo=15):
    d = date.today() + timedelta(days=minimo)
    while d.isoweekday() != iso:
        d += timedelta(days=1)
    return d


def iso(d, h, m=0):
    return f'{d.isoformat()}T{h:02d}:{m:02d}:00-03:00'


admin, barb, cli, sup = (login(e) for e in ('admin.a@exemplo.test', 'joao.barbeiro@exemplo.test', 'cliente1@exemplo.test', 'plataforma@exemplo.test'))
B1, B2, B3 = IDS['barbers']
CORTE, BARBA, COMBO = IDS['services'][:3]
SHOP = IDS['shop_a']
dom, sab, seg = proximo(7), proximo(6), proximo(1)
cid = cli.me['id']


def novo(sess, d, h, m=0, barbeiro=B1, servico=CORTE, **extra):
    return sess.post(f'{API}/appointments/', json={'cliente': cid, 'barbeiro': barbeiro, 'servico': servico, 'data_hora': iso(d, h, m), **extra})


# BUS-15 ----------------------------------------------------------------------
for st, quem, sess in (('confirmado', 'cliente', cli), ('cancelado', 'cliente', cli), ('realizado', 'cliente', cli)):
    r = novo(sess, seg, 9, status=st)
    rec(f'BUS-15/{quem}/{st}', f'{quem} cria com status={st}', '403', r.status_code, r.status_code == 403)
r = novo(cli, seg, 9)
rec('BUS-15/cliente/padrao', 'cliente cria sem status', '201 agendado', f"{r.status_code} {b(r).get('status')}", r.status_code == 201 and b(r).get('status') == 'agendado')
r = novo(admin, seg, 10, status='confirmado')
rec('BUS-15/admin/confirmado', 'admin registra já confirmado', '201 confirmado', f"{r.status_code} {b(r).get('status')}", r.status_code == 201 and b(r).get('status') == 'confirmado')
r = novo(barb, seg, 11, status='cancelado')
rec('BUS-15/barbeiro/cancelado', 'barbeiro cria já cancelado', '400', r.status_code, r.status_code == 400)

# BUS-03 ----------------------------------------------------------------------
a = novo(cli, seg, 13).json()
admin.patch(f"{API}/appointments/{a['id']}/", json={'status': 'confirmado'})
r = cli.patch(f"{API}/appointments/{a['id']}/", json={'data_hora': iso(seg, 14)})
rec('BUS-03/cliente/horario', 'cliente remarca confirmado', '200 agendado', f"{r.status_code} {b(r).get('status')}", b(r).get('status') == 'agendado')
admin.patch(f"{API}/appointments/{a['id']}/", json={'status': 'confirmado'})
r = cli.patch(f"{API}/appointments/{a['id']}/", json={'observacoes': 'só observação'})
rec('BUS-03/cliente/observacoes', 'cliente edita só observações', '200 confirmado', f"{r.status_code} {b(r).get('status')}", b(r).get('status') == 'confirmado')
r = admin.patch(f"{API}/appointments/{a['id']}/", json={'data_hora': iso(seg, 15)})
rec('BUS-03/admin/horario', 'admin remarca confirmado', '200 confirmado', f"{r.status_code} {b(r).get('status')}", b(r).get('status') == 'confirmado')

# BUS-05 ----------------------------------------------------------------------
for nome, payload in (('completo', {'horario_abertura': '18:00:00', 'horario_fechamento': '08:00:00'}),
                      ('parcial', {'horario_fechamento': '08:30:00'}),
                      ('igual', {'horario_fechamento': '09:00:00'}),
                      ('meia-noite', {'horario_abertura': '22:00:00', 'horario_fechamento': '02:00:00'})):
    r = admin.patch(f'{API}/barbershops/{SHOP}/', json=payload)
    rec(f'BUS-05/{nome}', f'admin salva horário {nome}', '400', f"{r.status_code} {str(b(r))[:90]}", r.status_code == 400)
shop = admin.get(f'{API}/barbershops/{SHOP}/').json()
rec('BUS-05/inalterado', 'horário gravado continua 09:00–19:00', '09:00:00–19:00:00', f"{shop['horario_abertura']}–{shop['horario_fechamento']}",
    (shop['horario_abertura'], shop['horario_fechamento']) == ('09:00:00', '19:00:00'))

# BUS-04 ----------------------------------------------------------------------
a = novo(cli, seg, 18, 30).json()
for quem, sess in (('admin', admin), ('cliente', cli)):
    r = sess.patch(f"{API}/appointments/{a['id']}/", json={'servico': COMBO})
    rec(f'BUS-04/{quem}', f'{quem} troca 30→60 min às 18:30 (fecha 19:00)', '400', f"{r.status_code} {str(b(r))[:90]}", r.status_code == 400)
a2 = novo(admin, seg, 18, barbeiro=B2).json()  # outro barbeiro: sem conflito com o horário das 18:30
r = admin.patch(f"{API}/appointments/{a2['id']}/", json={'servico': COMBO})
rec('BUS-04/limite', 'troca 30→60 min às 18:00 (termina 19:00)', '200', r.status_code, r.status_code == 200)

# BUS-06 ----------------------------------------------------------------------
slots_dom_padrao = cli.get(f'{API}/appointments/available-slots/', params={'barbeiro': B1, 'servico': CORTE, 'data': dom.isoformat()}).json()['slots']
rec('BUS-06/padrao', 'padrão (todos os dias): domingo continua aberto', 'horários no domingo', f'{len(slots_dom_padrao)} horários', len(slots_dom_padrao) > 0)
for quem, sess in (('cliente', cli), ('barbeiro', barb)):
    r = sess.patch(f'{API}/barbershops/{SHOP}/', json={'dias_funcionamento': [1, 2, 3, 4, 5, 6]})
    rec(f'BUS-06/config/{quem}', f'{quem} tenta mudar os dias', '403', r.status_code, r.status_code == 403)
r = admin.patch(f'{API}/barbershops/{SHOP}/', json={'dias_funcionamento': []})
rec('BUS-06/config/vazio', 'admin salva sem nenhum dia', '400', r.status_code, r.status_code == 400)
r = admin.patch(f'{API}/barbershops/{SHOP}/', json={'dias_funcionamento': [1, 2, 3, 4, 5, 6]})
rec('BUS-06/config/admin', 'admin fecha o domingo', '200 [1..6]', f"{r.status_code} {b(r).get('dias_funcionamento')}", r.status_code == 200 and b(r).get('dias_funcionamento') == [1, 2, 3, 4, 5, 6])
sl = cli.get(f'{API}/appointments/available-slots/', params={'barbeiro': B1, 'servico': CORTE, 'data': dom.isoformat()}).json()['slots']
ss = cli.get(f'{API}/appointments/available-slots/', params={'barbeiro': B1, 'servico': CORTE, 'data': sab.isoformat()}).json()['slots']
rec('BUS-06/slots', 'horários: domingo x sábado', 'domingo 0; sábado > 0', f'domingo {len(sl)}; sábado {len(ss)}', not sl and ss)
for quem, sess in (('cliente', cli), ('admin', admin), ('barbeiro', barb)):
    r = novo(sess, dom, 10)
    rec(f'BUS-06/agendar/{quem}', f'{quem} agenda no domingo fechado', '400', f"{r.status_code} {str(b(r))[:80]}", r.status_code == 400)
s1 = novo(cli, sab, 10)
rec('BUS-06/sabado', 'cliente agenda no sábado aberto', '201', s1.status_code, s1.status_code == 201)
if s1.status_code == 201:
    r = cli.patch(f"{API}/appointments/{s1.json()['id']}/", json={'data_hora': iso(dom, 10)})
    rec('BUS-06/remarcar', 'cliente remarca para o domingo fechado', '400', r.status_code, r.status_code == 400)
# restaura a configuração padrão para não afetar outros testes
admin.patch(f'{API}/barbershops/{SHOP}/', json={'dias_funcionamento': [1, 2, 3, 4, 5, 6, 7]})

json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
ok = sum(x['ok'] for x in out)
print(f'{len(out)} verificações; {ok} conforme; {len(out) - ok} divergentes')
for x in out:
    print('OK ' if x['ok'] else ' X ', x['id'], '|', str(x['obtido'])[:100])
