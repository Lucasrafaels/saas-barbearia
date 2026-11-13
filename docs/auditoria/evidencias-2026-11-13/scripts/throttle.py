"""Rate limit real do projeto (login 5/min) com 3 workers do gunicorn, cache padrão."""
import collections, requests
codes = []
for i in range(15):
    s = requests.Session()  # nova conexão a cada tentativa: o gunicorn distribui entre os workers
    r = s.post('http://127.0.0.1:8766/api/v1/auth/login/', json={'email': 'naoexiste@exemplo.test', 'password': 'errada'},
               headers={'Connection': 'close'})
    codes.append(r.status_code)
print('15 tentativas de login com senha errada no mesmo minuto, mesmo IP, 3 workers:')
print(' sequência:', codes)
print(' contagem:', dict(collections.Counter(codes)))
print(' tentativas aceitas (401) antes/apesar do limite de 5/min:', codes.count(401))
