"""
AUTH-04/05 — análise de equivalência ANTES de implementar: a normalização em Python (strip + lower) e as funções do
PostgreSQL (lower, btrim) no banco DESCARTÁVEL eq_db (PG 18.3, pt_BR.UTF-8, libc, 127.0.0.1:55432), ponto de código por
ponto de código, mais o que o EmailValidator do Django aceita. Sem banco real, sem rede.
Uso: venv/bin/python equivalencia_python_postgresql.py <saida.json>
"""
import json
import sys
import unicodedata

import psycopg2

sys.path.insert(0, '/home/lucasrafael/arquivos_faculdade/saas_barbearia')
import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.configure(USE_I18N=False)
django.setup()
from django.core.exceptions import ValidationError  # noqa: E402
from django.core.validators import validate_email  # noqa: E402
from rest_framework import serializers  # noqa: E402

con = psycopg2.connect(host='127.0.0.1', port=55432, user='smoke', dbname='eq_db')
cur = con.cursor()
cur.execute("select datcollate, datctype, datlocprovider, datcollversion, version() from pg_database where datname = current_database()")
banco = dict(zip(['datcollate', 'datctype', 'provider', 'collversion', 'version'], cur.fetchone()))
assert banco['datctype'].startswith('pt_BR'), banco
out = {'banco': banco, 'python_unicode': unicodedata.unidata_version, 'python': sys.version.split()[0]}

CODEPOINTS = [c for c in range(1, 0x110000) if not 0xD800 <= c <= 0xDFFF]


def aceito(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def pg_map(func, textos, lote=50000):
    res = []
    for i in range(0, len(textos), lote):
        cur.execute(f'select {func}(t) from unnest(%s::text[]) with ordinality u(t, n) order by n', [textos[i:i + lote]])
        res += [r[0] for r in cur.fetchall()]
    return res


# 1. lower() caractere a caractere, e o "ponto fixo": o que o Python grava passa no CHECK email = lower(email)?
chars = [chr(c) for c in CODEPOINTS]
pg_lower = pg_map('lower', chars)
py_lower = [ch.lower() for ch in chars]
pg_lower_do_py = pg_map('lower', py_lower)
diverge = [c for c, a, b in zip(CODEPOINTS, py_lower, pg_lower) if a != b]
nao_fixo = [c for c, a, b in zip(CODEPOINTS, py_lower, pg_lower_do_py) if a != b]
out['lower_total_de_pontos'] = len(CODEPOINTS)
out['lower_divergentes'] = len(diverge)
out['lower_divergentes_ascii'] = [c for c in diverge if c < 128]
out['lower_python_que_violaria_o_check'] = len(nao_fixo)


def no_dominio(c):
    return aceito(f'x@a{chr(c)}b.test')


div_aceitos = [c for c in diverge if c >= 128 and no_dominio(c)]
fixo_aceitos = [c for c in nao_fixo if c >= 128 and no_dominio(c)]
amostra = lambda lst: [{'cp': f'U+{c:04X}', 'nome': unicodedata.name(chr(c), '?'), 'python_lower': [f'U+{ord(x):04X}' for x in chr(c).lower()],  # noqa: E731
                        'pg_lower': [f'U+{ord(x):04X}' for x in pg_lower[CODEPOINTS.index(c)]]} for c in lst[:12]]
out['lower_divergentes_aceitos_pelo_EmailValidator_no_dominio'] = len(div_aceitos)
out['lower_divergentes_aceitos_amostra'] = amostra(div_aceitos)
out['entradas_aceitas_cujo_lower_python_violaria_o_check'] = len(fixo_aceitos)
out['entradas_aceitas_violariam_check_amostra'] = amostra(fixo_aceitos)

# 2. Espaços externos: Python strip (DRF, forms do Django, normalize_email) × PostgreSQL btrim() e \s.
py_espacos = [c for c in CODEPOINTS if chr(c).isspace()]
cur.execute("select c from unnest(%s::int[]) c where btrim(chr(c) || 'a' || chr(c)) = 'a'", [py_espacos])
pg_btrim = [r[0] for r in cur.fetchall()]
cur.execute("select c from generate_series(1, 1114111) c where c not between 55296 and 57343 and chr(c) ~ '^\\s$'")
pg_classe_s = [r[0] for r in cur.fetchall()]
drf = serializers.CharField()
drf_remove = [c for c in py_espacos if drf.to_internal_value(chr(c) + 'a' + chr(c)) == 'a']
fmt = lambda lst: [f'U+{c:04X}' for c in lst]  # noqa: E731
out['espacos'] = {
    'python_strip_e_drf': fmt(py_espacos), 'drf_trim_whitespace_igual_ao_python': drf_remove == py_espacos,
    'postgresql_btrim_padrao_remove': fmt(pg_btrim), 'postgresql_regex_s_pt_BR': fmt(pg_classe_s),
    'python_mas_nao_regex_s_do_postgresql': fmt(sorted(set(py_espacos) - set(pg_classe_s))),
    'regex_s_do_postgresql_mas_nao_python': fmt(sorted(set(pg_classe_s) - set(py_espacos))),
}

# 3. Invisíveis que o EmailValidator aceita pelo caminho IDNA (o valor gravado continua com o caractere).
invisiveis = [0x00AD, 0x034F, 0x180B, 0x200B, 0x200C, 0x200D, 0x2060, 0xFE00, 0xFE0F, 0xFEFF]
inv = []
for c in invisiveis:
    for pos, e in (('no meio do domínio', f'x@exem{chr(c)}plo.test'), ('no fim', f'x@exemplo.test{chr(c)}'),
                   ('na parte local', f'x{chr(c)}y@exemplo.test')):
        inv.append({'cp': f'U+{c:04X}', 'nome': unicodedata.name(chr(c), '?'), 'posicao': pos, 'aceito': aceito(e),
                    'python_strip_remove': e.strip() != e})
out['invisiveis_no_EmailValidator'] = inv
out['invisiveis_aceitos'] = sum(1 for i in inv if i['aceito'])

# 4. Regra alternativa: só ASCII imprimível sem espaço (0x21-0x7E). Equivalência exata?
ascii_imp = list(range(0x21, 0x7F))
out['ascii_lower_python_igual_postgresql'] = all(chr(c).lower() == pg_lower[CODEPOINTS.index(c)] for c in range(1, 128))
cur.execute("select count(*) from generate_series(1, 1114111) c where c not between 55296 and 57343 "
            "and (chr(c) ~ '^[!-~]$') <> (c between 33 and 126)")
out['regex_faixa_ascii_divergencias_em_todos_os_pontos'] = cur.fetchone()[0]
cur.execute("select count(*) from generate_series(1, 1114111) c where c not between 55296 and 57343 "
            "and (octet_length(chr(c)) = 1) <> (c < 128)")
out['octet_length_1_igual_ascii_divergencias'] = cur.fetchone()[0]
out['ascii_imprimiveis_aceitos_em_algum_ponto_do_email'] = sum(
    1 for c in ascii_imp if aceito(f'a{chr(c)}b@exemplo.test') or aceito(f'x@a{chr(c)}b.test'))
con.close()
print(json.dumps({k: v for k, v in out.items() if k not in ('espacos', 'invisiveis_no_EmailValidator')}, ensure_ascii=False, indent=1))
print(json.dumps({k: (v if k.endswith('igual_ao_python') or len(v) < 40 else f'{len(v)} pontos') for k, v in out['espacos'].items()}, ensure_ascii=False, indent=1))
print('invisíveis aceitos:', out['invisiveis_aceitos'], 'de', len(inv))
for i in inv:
    if i['aceito']:
        print('  aceito:', i['cp'], i['nome'], i['posicao'], '| strip remove:', i['python_strip_remove'])
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
