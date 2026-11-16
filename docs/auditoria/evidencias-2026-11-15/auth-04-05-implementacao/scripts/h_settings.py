"""AUTH-04/05 (implementação): API de laboratório sobre um banco DESCARTÁVEL (PG 18.3 pt_BR, 127.0.0.1:55432).
O banco vem de H_DB; a pasta de e-mails, de H_MAIL. Limites relaxados só aqui (o assunto é o e-mail, não a mitigação D)."""
import os

from config.settings import *  # noqa: F401,F403

_DB = os.environ['H_DB']
assert _DB in ('h_novo_f', 'h_novo_t', 'h_ant_f'), _DB
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': _DB, 'USER': 'smoke', 'PASSWORD': '',
                         'HOST': '127.0.0.1', 'PORT': '55432'}}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
ALLOWED_HOSTS = ['127.0.0.1']
SECURE_SSL_REDIRECT = False
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/ascii/media'
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {k: '100000/hour' for k in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']},  # noqa: F405
}
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.environ['H_MAIL']
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR'}}}
