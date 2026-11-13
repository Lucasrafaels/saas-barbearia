"""
Sondagem complementar da API isolada (banco descartável). Sem tokens/senhas na saída.
Uso: python probe2.py <state.json> <saida.json> <dir_tmp>
"""
import io
import json
import os
import statistics
import sys
import time as _time
from datetime import date, timedelta

import requests

API = 'http://127.0.0.1:8765/api/v1'
state = json.load(open(sys.argv[1]))
CREDS, IDS = state['creds'], state['ids']
TMP = sys.argv[3]
results = []


def rec(group, cid, desc, expected, actual, ok, note=''):
    results.append({'grupo': group, 'id': cid, 'verificacao': desc, 'esperado': expected,
                    'obtido': actual, 'ok': bool(ok), 'obs': note})


def login(email):
    s = requests.Session()
    r = s.post(f'{API}/auth/login/', json={'email': email, 'password': CREDS[email]})
    s.headers['Authorization'] = 'Bearer ' + r.json()['access']
    return s


def b(r):
    try:
        return r.json()
    except Exception:
        return r.text[:160]


def iso(d, hh, mm=0):
    return f'{d.isoformat()}T{hh:02d}:{mm:02d}:00-03:00'


admin, barb, cli = login('admin.a@exemplo.test'), login('joao.barbeiro@exemplo.test'), login('cliente1@exemplo.test')
B1, B2, B3 = IDS['barbers']
SV = IDS['services']
D = date.today() + timedelta(days=14)
while D.weekday() == 6:
    D += timedelta(days=1)

# BUS-12 refeito: barbeiro com agendamento próprio
r = barb.post(f'{API}/appointments/', json={'cliente': IDS['clientes'][2], 'barbeiro': B1, 'servico': SV[0], 'data_hora': iso(D, 10)})
aid = b(r).get('id')
r_del = barb.delete(f'{API}/appointments/{aid}/')
r_cli = barb.patch(f'{API}/appointments/{aid}/', json={'cliente': IDS['clientes'][3]})
r_can = barb.patch(f'{API}/appointments/{aid}/', json={'status': 'cancelado'})
rec('Regras de negócio', 'BUS-12', 'barbeiro: DELETE, troca de cliente e PATCH cancelado no próprio horário',
    'mesma regra para DELETE e PATCH; troca de cliente definida', f'criação={r.status_code}; DELETE={r_del.status_code}; '
    f'PATCH cliente={r_cli.status_code} (cliente agora={b(r_cli).get("cliente")}); PATCH cancelado={r_can.status_code}',
    not (r_del.status_code == 403 and r_can.status_code == 200))

# BUS-09: duração não histórica
svc = admin.post(f'{API}/services/', json={'nome': 'Serviço teste duração', 'preco': '30.00', 'duracao': 30}).json()
a1 = cli.post(f'{API}/appointments/', json={'cliente': IDS['clientes'][0], 'barbeiro': B2, 'servico': svc['id'], 'data_hora': iso(D, 10)}).json()
c2 = login('cliente2@exemplo.test')
a2 = c2.post(f'{API}/appointments/', json={'cliente': IDS['clientes'][1], 'barbeiro': B2, 'servico': svc['id'], 'data_hora': iso(D, 10, 30)}).json()
r = admin.patch(f'{API}/services/{svc["id"]}/', json={'duracao': 60}, params={'ativo': 'all'})
g1 = admin.get(f'{API}/appointments/{a1["id"]}/').json()
g2 = admin.get(f'{API}/appointments/{a2["id"]}/').json()
rec('Regras de negócio', 'BUS-09', 'alterar duração do serviço com dois horários seguidos (10:00 e 10:30)', 'horários existentes preservados',
    f'PATCH duracao={r.status_code}; 10:00 agora dura {g1["servico_duracao"]} min e termina às 11:00, sobrepondo 10:30 ({g2["status"]})',
    g1['servico_duracao'] == 30)

# BUS-14: admin agenda para cliente pela API
r = admin.post(f'{API}/appointments/', json={'cliente': IDS['clientes'][3], 'barbeiro': B1, 'servico': SV[0], 'data_hora': iso(D, 15)})
rec('Regras de negócio', 'BUS-14-api', 'admin agenda para cliente pela API', 201, r.status_code, r.status_code == 201, 'a API permite; falta tela')

# AUTH-02 por edição de e-mail
r = cli.patch(f"{API}/users/{IDS['clientes'][0]}/", json={'email': 'CLIENTE2@exemplo.test'})
rec('Regras de negócio', 'AUTH-02c', 'cliente troca o próprio e-mail para variação em maiúsculas de outro cliente', 400, r.status_code, r.status_code == 400)
if r.status_code == 200:
    cli.patch(f"{API}/users/{IDS['clientes'][0]}/", json={'email': 'cliente1@exemplo.test'})

# Validação de campos da barbearia
r = admin.patch(f"{API}/barbershops/{IDS['shop_a']}/", json={'telefone': 'abc-não-é-telefone'})
rec('Regras de negócio', 'VAL-01', 'telefone da barbearia sem validação de formato', 400, r.status_code, r.status_code == 400)
admin.patch(f"{API}/barbershops/{IDS['shop_a']}/", json={'telefone': '11900000000'})
r = admin.post(f'{API}/services/', json={'nome': 'Corte', 'preco': '45.00', 'duracao': 30})
rec('Regras de negócio', 'VAL-02', 'serviço com nome duplicado no mesmo tenant', 400, r.status_code, r.status_code == 400)
r = admin.post(f'{API}/services/', json={'nome': 'Serviço eterno', 'preco': '999999.99', 'duracao': 100000})
rec('Regras de negócio', 'VAL-03', 'serviço com duração de 100.000 min e preço 999.999,99', 400, r.status_code, r.status_code == 400)

# Upload de logo: arquivo grande e SVG
from PIL import Image  # noqa: E402
import random  # noqa: E402
random.seed(1)
img = Image.frombytes('RGB', (2200, 2200), os.urandom(2200 * 2200 * 3))
big = io.BytesIO(); img.save(big, format='PNG'); size_mb = len(big.getvalue()) / 1e6
up = requests.patch(f"{API}/barbershops/{IDS['shop_a']}/", headers={'Authorization': admin.headers['Authorization']},
                    files={'logo': ('logo.png', big.getvalue(), 'image/png')})
rec('Segurança', 'UPL-01', f'upload de logo PNG de {size_mb:.1f} MB', '400 (limite de tamanho)', f"{up.status_code} logo={'definido' if b(up).get('logo') else None}",
    up.status_code == 400)
svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
up = requests.patch(f"{API}/barbershops/{IDS['shop_a']}/", headers={'Authorization': admin.headers['Authorization']},
                    files={'logo': ('logo.svg', svg, 'image/svg+xml')})
rec('Segurança', 'UPL-02', 'upload de SVG com script', 400, up.status_code, up.status_code == 400)

# Tempo de resposta da recuperação de senha (oráculo por tempo)
def t(email):
    t0 = _time.perf_counter(); requests.post(f'{API}/auth/password/reset/', json={'email': email}); return (_time.perf_counter() - t0) * 1000
ex = [t('cliente6@exemplo.test') for _ in range(12)]
no = [t(f'naoexiste{i}@exemplo.test') for i in range(12)]
rec('Segurança', 'SES-10b', 'tempo da recuperação: e-mail existente x inexistente (12 amostras)', 'tempos equivalentes',
    f'mediana existente={statistics.median(ex):.0f} ms; inexistente={statistics.median(no):.0f} ms',
    abs(statistics.median(ex) - statistics.median(no)) < 15)

# Rebaixar barbeiro por /users/ deixa horários futuros
fut = [a for a in admin.get(f'{API}/appointments/', params={'barbeiro': B2}).json()['results']
       if a['status'] in ('agendado', 'confirmado')]
r = admin.patch(f"{API}/users/{IDS['barber_users'][1]}/", json={'tipo_perfil': 'cliente'})
still = [a for a in admin.get(f'{API}/appointments/', params={'barbeiro': B2}).json()['results'] if a['status'] in ('agendado', 'confirmado')]
rec('Regras de negócio', 'BUS-13b', 'rebaixar barbeiro a cliente por /users/', 'tratar horários futuros', f'PATCH={r.status_code}; {len(still)} horários ativos permanecem', not still)
# Ex-barbeiro (agora cliente) ainda consegue confirmar? Não: queryset vazio. Já o cliente que agendou com ele vê o horário.

# /users/me/ só GET
r = cli.patch(f'{API}/users/me/', json={'nome': 'x'})
rec('Contrato', 'CTR-01', 'PATCH /users/me/', 405, r.status_code, r.status_code == 405)
r = requests.Session(); r.headers.update(cli.headers)
r = r.post(f'{API}/appointments/', json={'barbeiro': B1, 'servico': SV[0], 'data_hora': iso(D, 17)})
rec('Contrato', 'CTR-02', 'cliente agenda sem enviar o próprio id em "cliente"', 201, f'{r.status_code} {json.dumps(b(r), ensure_ascii=False)[:80]}', r.status_code == 201,
    'o backend sobrescreve o cliente, mas exige o campo')

json.dump(results, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
for x in results:
    print('OK ' if x['ok'] else ' X ', x['id'], '-', x['verificacao'][:70], '|', str(x['obtido'])[:150])
