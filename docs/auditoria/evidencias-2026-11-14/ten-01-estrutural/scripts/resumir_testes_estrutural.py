"""Quadro antes/depois dos testes novos da correção estrutural do TEN-01, a partir dos logs -v 2 do Django."""
import collections
import re
import sys


def ler(caminho):
    s = open(caminho, encoding='utf-8').read()
    testes = []
    for m in re.finditer(r'^(test_\w+) \(config\.test_isolamento_tenant\.(\w+)\.\1\)', s, re.M):
        if (m.group(2), m.group(1)) not in testes:
            testes.append((m.group(2), m.group(1)))
    falhas = collections.Counter()
    for bloco in re.split(r'^={70}\n', s, flags=re.M):
        m = re.match(r'(FAIL|ERROR): (test_\w+) ', bloco)
        if m:
            falhas[m.group(2)] += 1
    return testes, falhas, re.search(r'^(OK.*|FAILED.*)$', s, re.M).group(1)


ta, fa, ra = ler(sys.argv[1])
tb, fb, rb = ler(sys.argv[2])
print('TEN-01, correção estrutural — testes novos (config/test_isolamento_tenant.py), SQLite em memória')
print('Código anterior = cópia do backend no estado HEAD + contenção do TEN-01 (config/tenancy.py copiado só para o import dos testes).')
print(f'Resultado no código anterior: {ra}')
print(f'Resultado no código corrigido: {rb}\n')
print(f'{"classe.teste":92} | anterior (subtestes com falha) | corrigido')
for classe, teste in tb:
    ant = 'passa' if not fa[teste] else f'{fa[teste]} falhas'
    dep = 'passa' if not fb[teste] else f'{fb[teste]} falhas'
    print(f'{classe + "." + teste:92} | {ant:30} | {dep}')
print(f'\nTestes que falham no código anterior: {sum(1 for _, t in tb if fa[t])} de {len(tb)}. '
      'Os que passam nas duas versões protegem fluxos legítimos (cliente, barbeiro, admin, superusuário) e propriedades já existentes.')
