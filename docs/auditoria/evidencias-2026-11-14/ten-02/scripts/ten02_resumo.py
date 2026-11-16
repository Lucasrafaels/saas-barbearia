"""Resumo da sondagem HTTP+SQL do TEN-02 nas cinco instâncias (código da auditoria, anterior e corrigido)."""
import json, re, sys
d = sys.argv[1]
VERS = ['auditoria-debug-true', 'anterior-debug-true', 'anterior-debug-false', 'corrigido-debug-true', 'corrigido-debug-false']
R = {v: json.load(open(f'{d}/ten02-{v}.json')) for v in VERS}
TEN = ('appointments_appointment', 'barbershops_barber', 'services_service', 'barbershops_barbershop')
norm = lambda t: re.sub(r'\d+', '<n>', t)

def sem_escopo(sql):
    """Comando em tabela de tenant sem condição de barbearia no WHERE (lê registro por ID, de qualquer barbearia)."""
    if not any(f'"{t}"' in sql for t in TEN):
        return False
    onde = sql.split(' WHERE ', 1)[1] if ' WHERE ' in sql else ''
    return 'barbershop_id' not in onde and '"barbeiro_id" =' not in onde

print('TEN-02 — sondagem HTTP com o SQL executado pelo servidor (log do PostgreSQL descartável, log_statement=all)\n')
pares = {
    'criação: ocupado x livre x barbeiro de B x inexistente': ('sem barbearia: criação', ['1 horário ocupado de B', '2 horário livre de B', '3 barbeiro válido de B', '4 IDs inexistentes']),
    'criação: corpo vazio': ('sem barbearia: criação', ['corpo vazio']),
    'PATCH: agendamento de B x inexistente': ('sem barbearia: demais operações', ['PATCH agendamento de B', 'PATCH inexistente']),
    'DELETE: agendamento de B x inexistente': ('sem barbearia: demais operações', ['DELETE agendamento de B', 'DELETE inexistente']),
    'horários livres: dia ocupado x livre x inexistente': ('sem barbearia: demais operações', ['horários livres, dia ocupado de B', 'horários livres, dia livre de B', 'horários livres, IDs inexistentes']),
    'lista filtrada: barbeiro de B x inexistente': ('sem barbearia: demais operações', ['lista filtrada pelo barbeiro de B', 'lista filtrada por ID inexistente']),
    'cliente A: barbeiro de B ocupado x livre x inexistente': ('cliente A contra a agenda de B', None),
    'admin A: barbeiro de B ocupado x livre x inexistente': ('admin A contra a agenda de B', None),
}
for v in VERS:
    print(f'== {R[v]["rotulo"]}')
    casos = R[v]['casos']
    for rot, (grupo, nomes) in pares.items():
        cs = [c for c in casos if c['grupo'] == grupo and (nomes is None or c['caso'] in nomes)]
        respostas = {(c['status'], c['resposta']) for c in cs}
        respostas_n = {(c['status'], norm(c['resposta'])) for c in cs}
        agenda = sum(len(c['agenda_consultada']) for c in cs)
        lidos = sum(sem_escopo(s) for c in cs for s in c['sql'])
        # Usuários que não são o solicitante, lidos sem condição de barbearia (ex.: o cliente de B no campo `cliente`).
        outros = sum(1 for c in cs for x in c['sql'] if '"accounts_user"' in x and ' WHERE ' in x
                     and not re.search(rf'"accounts_user"\."id" = {c["solicitante"]}\b', x) and 'barbershop_id' not in x.split(' WHERE ', 1)[1])
        print(f'   {rot}: status {sorted({c["status"] for c in cs})}; respostas distintas {len(respostas)} '
              f'(sem números: {len(respostas_n)}); consultas à agenda {agenda}; leituras sem escopo de barbearia {lidos}; usuários alheios lidos sem escopo {outros}')
    leg = [c for c in casos if c['grupo'] == 'cliente A na própria barbearia']
    print(f'   cliente A na própria barbearia: {[(c["caso"], c["status"]) for c in leg]}; consultas à agenda {sum(len(c["agenda_consultada"]) for c in leg)}')
    ob = [c for c in casos if c['grupo'] == 'cadastro público e onboarding']
    print(f'   cadastro público e onboarding: {[(c["caso"], c["status"]) for c in ob]}\n')

print('SQL executado pelo servidor para "sem barbearia, 1 horário ocupado de B":')
for v in ('auditoria-debug-true', 'anterior-debug-true', 'corrigido-debug-true', 'corrigido-debug-false'):
    c = next(c for c in R[v]['casos'] if c['caso'] == '1 horário ocupado de B')
    print(f'-- {v}: {c["status"]} {c["resposta"][:120]}')
    for s in c['sql']:
        print(f'     {s}')
print('\nSQL executado pelo servidor para "cliente A na própria barbearia, conflito" (validação legítima da agenda de A):')
c = next(c for c in R['corrigido-debug-true']['casos'] if c['caso'].startswith('mesmo horário'))
print(f'-- corrigido-debug-true: {c["status"]} {c["resposta"][:120]}')
for s in [x for x in c['sql'] if 'appointments_appointment' in x and 'barbeiro_id' in x]:
    print(f'     {s}')
print('   (o barbeiro_id é o barbeiro de A escolhido pelo próprio cliente de A)')
