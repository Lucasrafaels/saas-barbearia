"""
Test settings using SQLite to avoid PostgreSQL collation issues.
"""
from .settings import *

# Use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Keep migrations enabled for SQLite :memory: to create tables
# MIGRATION_MODULES = DisableMigrations()

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable throttling for tests but keep rates for throttle scopes
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
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

# Use weaker JWT settings for tests
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# Disable CORS for tests
CORS_ALLOW_ALL_ORIGINS = True