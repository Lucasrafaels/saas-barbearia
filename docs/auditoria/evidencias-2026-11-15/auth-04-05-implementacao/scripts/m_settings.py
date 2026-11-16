"""accounts.0006 (validação): banco DESCARTÁVEL vindo de M_DB (PG 18.3 pt_BR, 127.0.0.1:55432)."""
import os

from config.settings import *  # noqa: F401,F403

_DB = os.environ['M_DB']
assert _DB in ('m_legado', 'm_valido'), _DB
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': _DB, 'USER': 'smoke', 'PASSWORD': '',
                         'HOST': '127.0.0.1', 'PORT': '55432'}}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/ascii/media'
