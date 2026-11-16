"""API isolada da auditoria multi-tenant: mesmo código, banco DESCARTÁVEL (PG 18 em 127.0.0.1:55432) e mídia fora do projeto."""
from config.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'iso_db', 'USER': 'smoke', 'PASSWORD': '',
        'HOST': '127.0.0.1', 'PORT': '55432',
    }
}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['NAME'] == 'iso_db'
MEDIA_ROOT = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/61af1f5c-5709-41df-b16b-b2a7a28636f3/scratchpad/iso/media'
CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:4181']
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {k: '100000/hour' for k in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']},  # noqa: F405
}
