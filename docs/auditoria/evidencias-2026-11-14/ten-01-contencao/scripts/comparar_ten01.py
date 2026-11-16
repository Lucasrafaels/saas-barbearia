"""Resumo e comparação das sondagens HTTP do TEN-01: código anterior x corrigido, DEBUG=True x DEBUG=False."""
import collections
import json
import sys

d = sys.argv[1]
R = {n: json.load(open(f'{d}/ten01-{n}.json')) for n in ('antes-debug-true', 'antes-debug-false', 'depois-debug-true', 'depois-debug-false')}
chave = lambda x: (x['rota'], x['variante'], x['papel'])

for n, r in R.items():
    res = r['resultados']
    html = [x for x in res if x['html']]
    vaz = [x for x in res if x['n_marcas_alheias'] or x['opcoes_alheias']]
    print(f'== {r["rotulo"]}: {len(res)} pedidos | HTML: {len(html)} | com dados de outro tenant: {len(vaz)} | 500: {sum(x["status"] >= 500 for x in res)} | OPTIONS renders={r["options"]["renders"]}')
    for tipo in ('html', 'navegador', 'json'):
        sub = [x for x in res if x['tipo'] == tipo]
        st = collections.Counter(x['status'] for x in sub)
        ct = collections.Counter(x['content_type'] for x in sub)
        print(f'   pedidos "{tipo}": {len(sub)} | status {dict(sorted(st.items()))} | content-type {dict(ct)} | HTML {sum(x["html"] for x in sub)} | com dados alheios {sum(bool(x["n_marcas_alheias"] or x["opcoes_alheias"]) for x in sub)}')
    if vaz:
        por = collections.defaultdict(set)
        for x in vaz:
            por[(x['rota'], x['papel'])].add(x['variante'])
        print('   vazamentos (rota | papel | formas de pedido | maior nº de <option> alheios | exemplos de nomes alheios):')
        for (rota, papel), vs in sorted(por.items()):
            xs = [x for x in vaz if x['rota'] == rota and x['papel'] == papel]
            mx = max(sum(x['opcoes_alheias'].values()) for x in xs)
            ex = sorted({m for x in xs for m in x['marcas_alheias']})[:4]
            print(f'     {rota} | {papel} | {len(vs)} formas | {mx} | {ex}')
    erros = [x for x in res if x['status'] >= 500]
    if erros:
        print('   respostas 500:', dict(collections.Counter((x['rota'], x['papel'], x['tipo']) for x in erros)))

print()
for modo in ('debug-true', 'debug-false'):
    a = {chave(x): x for x in R[f'antes-{modo}']['resultados']}
    b = {chave(x): x for x in R[f'depois-{modo}']['resultados']}
    assert a.keys() == b.keys()
    for tipo in ('json', 'navegador'):
        ks = [k for k in a if a[k]['tipo'] == tipo]
        dif = [k for k in ks if a[k]['status'] != b[k]['status']]
        print(f'[{modo}] pedidos "{tipo}": {len(ks)}; status igual antes e depois em {len(ks) - len(dif)}; diferentes: {len(dif)}')
        for k in dif:
            print(f'     {k}: {a[k]["status"]} {a[k]["content_type"]} -> {b[k]["status"]} {b[k]["content_type"]}')
    ks = [k for k in a if a[k]['tipo'] == 'html']
    print(f'[{modo}] pedidos de HTML depois: status {dict(collections.Counter(b[k]["status"] for k in ks))}; '
          f'corpo só com "detail": {sum(b[k]["corpo_json_detail"] for k in ks)}/{len(ks)}')
print()
igual = all(
    {chave(x): (x['status'], x['content_type'], x['html']) for x in R[f'{fase}-debug-true']['resultados']}
    == {chave(x): (x['status'], x['content_type'], x['html']) for x in R[f'{fase}-debug-false']['resultados']}
    for fase in ('antes', 'depois'))
print(f'DEBUG=True e DEBUG=False dão os mesmos status, content-types e formato, antes e depois: {igual}')
