"""AUTH-04/AUTH-05 (investigação): código atual SEM alteração, banco DESCARTÁVEL (PG 18.3, 127.0.0.1:55432).
O banco vem de A45_DB (a45_db para a API, a45_lab para os scripts no processo)."""
import os

from config.settings import *  # noqa: F401,F403

_DB = os.environ.get('A45_DB', 'a45_db')
assert _DB in ('a45_db', 'a45_lab'), _DB
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': _DB, 'USER': 'smoke', 'PASSWORD': '',
                         'HOST': '127.0.0.1', 'PORT': '55432'}}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'testserver']
SECURE_SSL_REDIRECT = False
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/a45/media'
# Os limites da mitigação D ficam altos SÓ neste laboratório: aqui se investiga o tratamento do e-mail, não o limite.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {k: '100000/hour' for k in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']},  # noqa: F405
}
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/a45/out/mail'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR'}}}
