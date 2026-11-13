"""
Configurações principais do projeto Django — Barbershop SaaS.

As variáveis sensíveis (SECRET_KEY, DATABASE_URL, DEBUG etc.) NÃO ficam
hardcoded aqui: são lidas do arquivo .env na raiz do projeto através da
biblioteca django-environ. Veja o .env.example para a lista completa.
"""
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Caminhos base e variáveis de ambiente
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
# Lê o .env na raiz do projeto (se existir). Em produção, normalmente as
# variáveis já vêm injetadas diretamente no ambiente pela infraestrutura.
environ.Env.read_env(str(BASE_DIR / '.env'))

_DEFAULT_DEV_SECRET = 'django-insecure-development-only-change-me-before-production-2026'
SECRET_KEY = env('SECRET_KEY', default=_DEFAULT_DEV_SECRET)
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'testserver'])

if not DEBUG and SECRET_KEY == _DEFAULT_DEV_SECRET:
    raise RuntimeError('SECRET_KEY deve ser definido em produção.')

# A SECRET_KEY assina os JWT (HS256, o SIMPLE_JWT não define SIGNING_KEY),
# as sessões e os links de redefinição de senha. O django-environ corta um
# valor sem aspas no primeiro "#", e isso já reduziu a chave local a poucos
# caracteres sem nenhum erro visível. Por isso a validação vale também com
# DEBUG=True. Os limites são os do check security.W009 do Django. A mensagem
# informa apenas o tamanho, nunca o valor.
SECRET_KEY_MIN_LENGTH = 50
SECRET_KEY_MIN_UNIQUE_CHARS = 5
if len(SECRET_KEY) < SECRET_KEY_MIN_LENGTH or len(set(SECRET_KEY)) < SECRET_KEY_MIN_UNIQUE_CHARS:
    raise ImproperlyConfigured(
        f'SECRET_KEY fraca: o valor carregado tem {len(SECRET_KEY)} caracteres; são '
        f'exigidos ao menos {SECRET_KEY_MIN_LENGTH} caracteres e '
        f'{SECRET_KEY_MIN_UNIQUE_CHARS} caracteres distintos. No .env, um "#" sem '
        'aspas inicia um comentário e trunca o valor. Gere uma chave sem caracteres '
        'especiais com: python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )


# ---------------------------------------------------------------------------
# Aplicações instaladas
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # permite invalidar refresh tokens no logout
    'corsheaders',
    'django_filters',
]

# Apps locais do projeto. "core" vem primeiro por não depender de mais
# nenhum outro app local (apenas fornece classes utilitárias/abstratas).
LOCAL_APPS = [
    'accounts',
    'barbershops',
    'services',
    'appointments',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # precisa vir antes do CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
# DATABASE_URL segue o formato: postgres://usuario:senha@host:porta/nome_do_banco
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default='postgres://barbershop_user:barbershop_pass@localhost:5433/barbershop_db',
    ),
}


# ---------------------------------------------------------------------------
# Usuário customizado e validação de senha
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
# Assumindo um público majoritariamente brasileiro (contexto de "barbearia").
# Ajuste LANGUAGE_CODE/TIME_ZONE se o produto for operar em outro país.
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Arquivos estáticos e de mídia (ex.: logo da barbearia)
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.DefaultPagination',
    'PAGE_SIZE': 20,
    # Habilitado globalmente; cada ViewSet decide se usa filterset_fields.
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    # Proteção geral contra abuso. Os endpoints de autenticação recebem
    # limites ainda mais restritivos e específicos nas respectivas views.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/minute',
        'register': '10/hour',
        'refresh': '10/minute',
        'logout': '30/minute',
        'password_change': '5/hour',
        'password_reset': '5/hour',
        'password_reset_confirm': '10/hour',
    },
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    # O hash de senha no token permite que uma troca de senha invalide o
    # access token imediatamente, sem aguardar a expiração de 15 minutos.
    'CHECK_REVOKE_TOKEN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# O refresh nunca é exposto ao JavaScript: o navegador o envia somente no
# cookie HttpOnly. O access permanece curto e é mantido apenas em memória.
JWT_REFRESH_COOKIE_NAME = 'barbearia_refresh'
JWT_REFRESH_COOKIE_PATH = '/api/v1/auth/'
JWT_REFRESH_COOKIE_SECURE = env.bool('JWT_REFRESH_COOKIE_SECURE', default=not DEBUG)
JWT_REFRESH_COOKIE_SAMESITE = env('JWT_REFRESH_COOKIE_SAMESITE', default='Lax')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@barbearia.local')


# ---------------------------------------------------------------------------
# CORS — libera o frontend React a consumir esta API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://127.0.0.1:5173'],
)
CORS_ALLOW_CREDENTIALS = True

# Segurança de transporte ativada por padrão fora do ambiente de
# desenvolvimento; as opções podem ser ajustadas pela infraestrutura.
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=not DEBUG)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=not DEBUG)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if env.bool(
    'USE_X_FORWARDED_PROTO', default=not DEBUG
) else None
X_FRAME_OPTIONS = 'DENY'
