"""
Mitigação D do TEN-03 — limitação documentada (SEC-13): sem NUM_PROXIES, o DRF usa o X-Forwarded-For enviado pelo
cliente como identidade da origem. Este script, sem banco e sem rede, mostra a chave que os limites por origem
(o 'register' que já existia e o 'register_day' novo) calculam em quatro pedidos. 198.51.100.7 e 203.0.113.x são
faixas reservadas para documentação.
Uso: DJANGO_SETTINGS_MODULE=config.test_settings python d_xff_identidade.py
"""
from unittest import mock

import django

django.setup()
from rest_framework.settings import api_settings  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from accounts.throttles import CadastroPublicoPorDiaThrottle  # noqa: E402

f = APIRequestFactory()
anon = mock.Mock(is_authenticated=False)
casos = [
    ('vítima, conexão direta', {'REMOTE_ADDR': '198.51.100.7'}),
    ('terceiro forjando X-Forwarded-For com o IP da vítima', {'REMOTE_ADDR': '127.0.0.1', 'HTTP_X_FORWARDED_FOR': '198.51.100.7'}),
    ('terceiro, valor forjado 1', {'REMOTE_ADDR': '127.0.0.1', 'HTTP_X_FORWARDED_FOR': '203.0.113.1'}),
    ('terceiro, valor forjado 2', {'REMOTE_ADDR': '127.0.0.1', 'HTTP_X_FORWARDED_FOR': '203.0.113.2'}),
]
print('NUM_PROXIES =', api_settings.NUM_PROXIES)
for nome, meta in casos:
    req = f.post('/api/v1/auth/register/', {}, format='json', **meta)
    req.user = anon
    print(f'{nome:55} -> chave {CadastroPublicoPorDiaThrottle().get_cache_key(req, None)}')
