"""
Configurações principais do projeto Django — Barbershop SaaS.

As variáveis sensíveis (SECRET_KEY, DATABASE_URL, DEBUG etc.) NÃO ficam
hardcoded aqui: são lidas do arquivo .env na raiz do projeto através da
biblioteca django-environ. Veja o .env.example para a lista completa.
"""
from datetime import timedelta
from pathlib import Path

import environ

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

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


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
        default='postgres://barbershop_user:barbershop_pass@localhost:5432/barbershop_db',
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
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# ---------------------------------------------------------------------------
# CORS — libera o frontend React a consumir esta API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:3000', 'http://127.0.0.1:3000'],
)
CORS_ALLOW_CREDENTIALS = True
