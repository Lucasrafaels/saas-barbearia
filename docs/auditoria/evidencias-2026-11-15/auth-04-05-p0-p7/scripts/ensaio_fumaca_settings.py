"""P7 — ensaio_settings (cópia descartável) com o e-mail capturado em ARQUIVOS LOCAIS, para seguir o token da recuperação.
Nada sai por SMTP. Limites de taxa: os reais (não relaxados)."""
from ensaio_settings import *  # noqa: F401,F403

assert DATABASES['default']['NAME'] == 'ensaio_restaurado' and DATABASES['default']['PORT'] == '55432'  # noqa: F405
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/claude-1000/-home-lucasrafael-arquivos-faculdade-saas-barbearia/b732fc01-eeb5-4087-becf-e69fa27549d7/scratchpad/p07/mail'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR'}}}
