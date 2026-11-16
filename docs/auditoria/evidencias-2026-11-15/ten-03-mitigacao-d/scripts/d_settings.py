"""Mitigação D do TEN-03: API de laboratório sobre um banco DESCARTÁVEL (PG 18.3, 127.0.0.1:55432).
O banco vem de D_DB (um dos quatro abaixo). As taxas de limite são as REAIS do código em teste (sem relaxar)."""
import os

from config.settings import *  # noqa: F401,F403

_DB = os.environ['D_DB']
assert _DB in ('d_novo_t', 'd_novo_f', 'd_ant_t', 'd_ant_f'), _DB
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': _DB, 'USER': 'smoke', 'PASSWORD': '',
                         'HOST': '127.0.0.1', 'PORT': '55432'}}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/d/media'
ALLOWED_HOSTS = ['127.0.0.1']
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR'}}}
