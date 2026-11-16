"""Compara, verificação por verificação, a sondagem de isolamento da auditoria (antes) com a repetida após a contenção do TEN-01."""
import json, sys
antes = {x['id']: x for x in json.load(open(sys.argv[1]))['resultados']}
depois = {x['id']: x for x in json.load(open(sys.argv[2]))['resultados']}
print(f'antes: {len(antes)} verificações, {sum(x["ok"] for x in antes.values())} conformes')
print(f'depois: {len(depois)} verificações, {sum(x["ok"] for x in depois.values())} conformes')
print(f'mesmos IDs: {sorted(antes) == sorted(depois)}')
mud = [i for i in antes if antes[i]['ok'] != depois.get(i, {}).get('ok')]
print(f'veredito alterado: {len(mud)}')
for i in mud:
    print(f"  {i}: {'conforme' if antes[i]['ok'] else 'DIVERGENTE'} -> {'conforme' if depois[i]['ok'] else 'DIVERGENTE'}")
    print(f"     antes : {antes[i]['observado'][:200]}")
    print(f"     depois: {depois[i]['observado'][:200]}")
print('divergentes que continuam:', ', '.join(f"{i} ({depois[i]['severidade']})" for i in depois if not depois[i]['ok']))
