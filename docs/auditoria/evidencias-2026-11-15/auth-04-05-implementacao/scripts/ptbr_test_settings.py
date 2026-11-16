"""Suíte de testes no PostgreSQL 18.3 DESCARTÁVEL com pt_BR.UTF-8 (libc), como o banco real. Nunca o .env nem o Docker."""
from config.test_settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'suite_ptbr', 'USER': 'smoke', 'PASSWORD': '',
        'HOST': '127.0.0.1', 'PORT': '55432',
        'TEST': {'NAME': 'test_suite_ptbr'},
    }
}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/ascii/media-testes'
