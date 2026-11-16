#!/usr/bin/env python3
"""
Mitigação D do TEN-03 — junta a cada pedido da sondagem o SQL que o PostgreSQL DESCARTÁVEL registrou entre os
marcadores, e resume as quatro instâncias (corrigido/anterior × DEBUG True/False).
Higienização: hashes de senha, tokens e jti nunca são copiados.
Uso: python3 -I d_resumo.py <pg.log> <pasta api> <resumo.txt>
"""
import json
import re
import sys
from collections import OrderedDict
from itertools import groupby

LOG, PASTA, RESUMO = sys.argv[1:4]
INSTANCIAS = OrderedDict([('8791', ('d_novo_t', 'corrigido', 'True')), ('8792', ('d_novo_f', 'corrigido', 'False')),
                          ('8793', ('d_ant_t', 'anterior', 'True')), ('8794', ('d_ant_f', 'anterior', 'False'))])
CAB = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ \S+ \[(\d+)\] (\S*) (LOG|ERROR|DETAIL|STATEMENT|HINT|WARNING):  ?(.*)$')
UNICIDADE = re.compile(r'SELECT 1 AS "a" FROM "accounts_user" WHERE .*"accounts_user"\."email" = ')


def higienizar(t):
    t = re.sub(r"pbkdf2_sha256\$[^']+", '<hash de senha removido>', t)
    t = re.sub(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', '<token removido>', t)
    return re.sub(r"'[0-9a-f]{32}'", "'<jti removido>'", t)


entradas = []
for linha in open(LOG, encoding='utf-8', errors='replace'):
    linha = linha.rstrip('\n')
    m = CAB.match(linha)
    if m:
        entradas.append({'db': m.group(2), 'tipo': m.group(3), 'texto': m.group(4)})
    elif entradas:
        entradas[-1]['texto'] += '\n' + linha

sql = {}
for banco in {v[0] for v in INSTANCIAS.values()}:
    atual = None
    for e in (x for x in entradas if x['db'] == banco):
        mk = re.search(r"DMARK (\S+) (inicio|fim)", e['texto'])
        if mk:
            atual = mk.group(1) if mk.group(2) == 'inicio' else None
            if atual:
                sql[(banco, atual)] = []
            continue
        if atual:
            texto = e['texto'][len('statement: '):] if e['texto'].startswith('statement: ') else e['texto']
            sql[(banco, atual)].append(f"[{e['tipo']}] {higienizar(texto)}")

dados = {}
for porta, (banco, versao, debug) in INSTANCIAS.items():
    regs = json.load(open(f'{PASTA}/sondagem_{porta}.json'))
    for r in regs:
        r['sql_do_servidor'] = sql.get((banco, r['id']), [])
        r['consultou_unicidade'] = any(UNICIDADE.search(s) for s in r['sql_do_servidor'])
    dados[porta] = regs
    json.dump(regs, open(f'{PASTA}/sondagem_{porta}_com_sql.json', 'w'), ensure_ascii=False, indent=1)


def sequencia(regs):
    return ', '.join(f'{n}×{s}' for s, n in ((k, len(list(g))) for k, g in groupby(r['status'] for r in regs)))


def normalizar(texto):
    return re.sub(r'\d+', 'N', texto)


saida = ['TEN-03, mitigação D — sondagem HTTP de antes e depois, com as taxas REAIS de cada versão do código.',
         'Bancos PG 18.3 DESCARTÁVEIS, um por instância. "Unicidade consultada" vem do log do próprio PostgreSQL.', '']
etapas = list(OrderedDict.fromkeys(r['etapa'] for r in dados['8791']))
for etapa in etapas:
    saida.append(f'== {etapa}: {dados["8791"][[r["etapa"] for r in dados["8791"]].index(etapa)]["pedido"]}')
    for porta, (banco, versao, debug) in INSTANCIAS.items():
        regs = [r for r in dados[porta] if r['etapa'] == etapa]
        bloqueados = [r for r in regs if r['status'] == 429]
        consultas_429 = sum(r['consultou_unicidade'] for r in bloqueados)
        consultas_ok = sum(r['consultou_unicidade'] for r in regs if r['status'] != 429)
        ras = sorted({r['retry_after'] for r in bloqueados}, key=lambda x: int(x))
        corpos = {normalizar(r['resposta']) for r in bloqueados}
        existentes = {normalizar(r['resposta']) for r in bloqueados if r['email_sondado'] and 'beta.test' in r['email_sondado']}
        livres = {normalizar(r['resposta']) for r in bloqueados if r['email_sondado'] and 'exemplo.test' in r['email_sondado']}
        linha = (f'  {versao:9} DEBUG={debug:5} | {sequencia(regs):40} | unicidade consultada: {consultas_ok} dos não limitados, '
                 f'{consultas_429} dos 429')
        if bloqueados:
            linha += f' | Retry-After: {", ".join(ras)} | corpos 429 distintos (sem os números): {len(corpos)}'
            if existentes and livres:
                linha += f' | existente × livre iguais: {existentes == livres}'
        saida.append(linha)
    saida.append('')

exemplo_429 = next(r for r in dados['8792'] if r['status'] == 429)
saida += ['Exemplo de 429 (corrigido, DEBUG=False): ' + exemplo_429['pedido'] + ' -> ' + exemplo_429['resposta']
          + f" | Content-Type: {exemplo_429['content_type']} | Retry-After: {exemplo_429['retry_after']}", '']
exemplo_429t = next(r for r in dados['8791'] if r['status'] == 429)
saida += ['Exemplo de 429 (corrigido, DEBUG=True): ' + exemplo_429t['pedido'] + ' -> ' + exemplo_429t['resposta']
          + f" | Content-Type: {exemplo_429t['content_type']}", '']
open(RESUMO, 'w').write('\n'.join(saida) + '\n')
print('\n'.join(saida))
