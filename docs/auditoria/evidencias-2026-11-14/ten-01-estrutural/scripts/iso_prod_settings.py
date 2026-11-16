"""Mesma API isolada, com DEBUG=False (comportamento de produção quanto aos renderizadores do DRF)."""
from iso_settings import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1']
