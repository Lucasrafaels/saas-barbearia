"""Resumo da sondagem HTTP+SQL do PER-13 nas quatro instâncias, com trechos de SQL e o achado separado (SEC-12)."""
import json, re, sys
d = sys.argv[1]
VERS = ['anterior-debug-true', 'anterior-debug-false', 'corrigido-debug-true', 'corrigido-debug-false']
print('PER-13 — GET/HEAD /api/v1/users/{id}/ no servidor real, com o SQL lido do log do PostgreSQL descartável (log_statement=all)\n')
for v in VERS:
    R = json.load(open(f'{d}/per13-{v}.json'))
    print(f'== {R["rotulo"]}: {json.dumps(R["geral"], ensure_ascii=False)}')
    for papel, r in R['resumo'].items():
        pedidos = [p for p in R['pedidos'] if p['papel'] == papel and p['metodo'] == 'GET' and p['alvo'] != 'o próprio']
        # A consulta da autenticação (a linha do próprio solicitante) não é busca de alvo.
        sem_tenant = sum(p['busca_sem_barbearia'] for p in pedidos) if papel != 'superusuário' else '—'
        print(f"   {papel:14} autorizados {r['GET autorizados']}; não autorizados {r['GET não autorizados']}: "
              f"resposta ≠ inexistente {r['GET não autorizados com resposta diferente da do inexistente']}, "
              f"SQL ≠ inexistente {r['GET não autorizados com SQL diferente da do inexistente (só números mudam)']}, "
              f"HEAD ≠ {r['HEAD não autorizados com status diferente do inexistente']}, "
              f"dados do alvo {r['respostas com dados do usuário consultado (não autorizados)']}, "
              f"busca do alvo sem barbearia {sem_tenant}, "
              f"busca sem o solicitante {r['buscas do alvo sem o solicitante no WHERE (cliente/barbeiro)']}")
    print()
print('SEC-12 (achado separado, não corrigido): PATCH com corpo vazio em outro usuário da mesma barbearia x inexistente')
for v in VERS:
    R = json.load(open(f'{d}/per13-{v}.json'))
    linhas = {papel: r['PATCH em outro usuário da mesma barbearia x inexistente (SEC-12)'] for papel, r in R['resumo'].items() if r['PATCH em outro usuário da mesma barbearia x inexistente (SEC-12)']}
    print(f'   {v}: {json.dumps(linhas, ensure_ascii=False)}')
print('\nSQL executado pelo servidor (cliente A consultando o barbeiro da mesma barbearia e um ID inexistente):')
for v in ('anterior-debug-false', 'corrigido-debug-false'):
    R = json.load(open(f'{d}/per13-{v}.json'))
    for alvo in ('barbeiro da mesma barbearia', 'inexistente'):
        p = next(p for p in R['pedidos'] if p['papel'] == 'cliente A' and p['metodo'] == 'GET' and p['alvo'] == alvo)
        print(f'-- {v} | {alvo} (id {p["alvo_id"]}; solicitante {p["solicitante"]}): {p["status"]} {p["resposta"][:90]}')
        for x in p['sql']:
            print('     ' + x[:230])
