"""Suíte de testes no PostgreSQL 18.3 DESCARTÁVEL (127.0.0.1:55432). Nunca o banco do .env."""
from config.test_settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ten01_suite', 'USER': 'smoke', 'PASSWORD': '',
        'HOST': '127.0.0.1', 'PORT': '55432',
        'TEST': {'NAME': 'test_ten01_suite'},
    }
}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/1849e68b-a8bd-402f-b975-c50f853b5427/scratchpad/iso/media-testes'
