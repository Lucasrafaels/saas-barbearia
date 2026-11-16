"""TEN-03 (simulação de laboratório, banco t3_lab): mesmo código do projeto, banco DESCARTÁVEL (PG 18.3 em 127.0.0.1:55432, t3_db) e mídia fora do projeto."""
from config.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 't3_lab', 'USER': 'smoke', 'PASSWORD': '',
        'HOST': '127.0.0.1', 'PORT': '55432',
        'TEST': {'NAME': 'test_t3_suite'},
    }
}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
assert DATABASES['default']['NAME'] in ('t3_lab',)
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/t3/media'
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'testserver']
SECURE_SSL_REDIRECT = False
# Limites relaxados só nesta instância de laboratório, para a matriz de cenários não ser barrada pelo throttle.
# Os limites reais (config/settings.py) são analisados à parte no relatório.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {k: '100000/hour' for k in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']},  # noqa: F405
}
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/t3/out/mail'
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR'}},
}
