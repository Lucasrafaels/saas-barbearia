"""
EXPERIMENTO DE LABORATÓRIO, FORA DO PROJETO. Mesma API isolada (banco descartável) com a API navegável
religada só nesta instância, para verificar o que os formulários HTML listariam se ela voltasse a ser
ativada. O config/settings.py do projeto continua só com JSONRenderer. Nunca use isto no projeto.
"""
from iso_settings import *  # noqa: F401,F403

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}
