"""
Plano da accounts.0006 (seção 32), passos P6 e P7 — settings do ENSAIO: a aplicação aponta para a CÓPIA RESTAURADA do
backup num PostgreSQL 18.3 DESCARTÁVEL (pt_BR.UTF-8, libc, 127.0.0.1:55432), nunca para o banco real.
NÃO EXECUTADO na etapa de planejamento. A cópia contém dados reais: fica só no diretório temporário e é apagada no fim.
"""
from config.settings import *  # noqa: F401,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'ensaio_restaurado', 'USER': 'smoke',
                         'PASSWORD': '', 'HOST': '127.0.0.1', 'PORT': '55432'}}
assert DATABASES['default']['PORT'] == '55432' and DATABASES['default']['HOST'] == '127.0.0.1'
assert DATABASES['default']['NAME'] == 'ensaio_restaurado'
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1']
SECURE_SSL_REDIRECT = False
# A cópia tem e-mails REAIS: nada pode sair por SMTP durante o ensaio.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
