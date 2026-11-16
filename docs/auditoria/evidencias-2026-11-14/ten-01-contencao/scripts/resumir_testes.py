"""Quadro antes/depois dos testes novos do TEN-01 a partir dos logs do executor do Django (-v 2)."""
import collections
import re
import sys


def ler(p):
    s = open(p, encoding='utf-8').read()
    falhas, erros, tipos = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    for b in re.split(r'^={70}\n', s, flags=re.M):
        m = re.match(r'(FAIL|ERROR): (test_\w+) .*?(?:\((.*)\))?\n', b)
        if not m:
            continue
        partes = b.split('\n' + '-' * 70 + '\n')
        b = partes[1] if len(partes) > 1 else b
        tipo, teste, params = m.groups()
        (falhas if tipo == 'FAIL' else erros)[teste] += 1
        ultima = [linha for linha in b.strip().splitlines() if linha.strip()][-1]
        motivo = ultima.split(':')[0] if tipo == 'ERROR' else re.sub(r"'[^']*'|\d+|\[.*\]", '…', ultima)[:90]
        v = re.search(r"variante='([^']*)'", params or '')
        tipos[teste][(tipo, v.group(1) if v else '—', motivo)] += 1
    return falhas, erros, tipos, re.search(r'^(OK.*|FAILED.*)$', s, re.M).group(1)


a, b = ler(sys.argv[1]), ler(sys.argv[2])
testes = ['test_pedidos_de_html_nao_recebem_html_nem_dados', 'test_pedidos_de_html_nao_recebem_html_nem_dados_com_debug',
          'test_casos_reproduzidos_na_auditoria', 'test_options_continua_em_json_e_so_anuncia_json',
          'test_nenhuma_view_registrada_reativa_renderizador_html', 'test_json_mantem_status_e_isolamento_de_cada_papel',
          'test_listas_json_trazem_os_dados_do_proprio_tenant', 'test_fluxo_do_frontend_com_axios_continua_funcionando',
          'test_escritas_do_admin_e_do_barbeiro_continuam_em_json', 'test_token_invalido_continua_recusado']
print('TEN-01 — testes novos (config/test_renderers.py), SQLite em memória')
print('Código anterior = cópia do backend com o settings.py do HEAD (sem DEFAULT_RENDERER_CLASSES). Código corrigido = projeto.')
print(f'Resultado no código anterior: {a[3]}')
print(f'Resultado no código corrigido: {b[3]}\n')
print(f'{"teste":62} | anterior (subtestes com falha/erro) | corrigido')
for t in testes:
    ant = 'passa' if a[0][t] + a[1][t] == 0 else f'{a[0][t]} falhas, {a[1][t]} erros'
    dep = 'passa' if b[0][t] + b[1][t] == 0 else f'{b[0][t]} falhas, {b[1][t]} erros'
    print(f'{t:62} | {ant:35} | {dep}')
print('\nMotivos no código anterior (quantidade × tipo | forma de pedido | última linha da falha, com valores trocados por …):')
for t in testes:
    if a[2][t]:
        print(f'- {t}')
        for (tipo, var, mot), n in sorted(a[2][t].items(), key=lambda x: -x[1]):
            print(f'    {n:4} × {tipo} | {var} | {mot}')
print('\nLeitura: "unexpectedly found" = a resposta era text/html; TypeError = sufixo de formato numa @action (API-03);')
print('AttributeError = o renderizador HTML chamou get_permissions() de agendamentos para o anônimo (AUTH-03);')
print('"False is not true" = o Accept de navegador recebia text/html em vez de JSON.')
