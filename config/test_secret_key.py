"""
SEC-01 — a SECRET_KEY efetivamente carregada precisa ser forte.

O `django-environ` corta um valor sem aspas no primeiro "#", e isso reduziu
a chave local a 3 caracteres sem nenhum erro. Como a mesma chave assina os
JWT (HS256), as sessões e os links de redefinição de senha, `settings.py`
passou a recusar chaves curtas em qualquer ambiente. Nenhum teste exibe o
valor da chave.
"""
import io
import os
import secrets
import subprocess
import sys
import warnings

import environ
from django.conf import settings
from django.test import SimpleTestCase
from jwt.warnings import InsecureKeyLengthWarning
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


def load_settings_in_subprocess(**env_overrides):
    """Importa config.settings num processo novo, com variáveis de ambiente próprias.

    Variáveis já presentes no ambiente têm precedência sobre o .env (o
    read_env usa setdefault), então o valor passado aqui é o que vale.
    """
    env = {**os.environ, **env_overrides}
    env.pop('DJANGO_SETTINGS_MODULE', None)
    return subprocess.run(
        [sys.executable, '-c', 'import config.settings'],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


class EffectiveSecretKeyTests(SimpleTestCase):
    def test_chave_efetiva_atende_ao_tamanho_minimo(self):
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50)
        self.assertGreaterEqual(len(set(settings.SECRET_KEY)), 5)

    def test_jwt_e_assinado_com_a_secret_key_completa(self):
        self.assertEqual(api_settings.ALGORITHM, 'HS256')
        self.assertEqual(api_settings.SIGNING_KEY, settings.SECRET_KEY)

    def test_assinar_e_validar_jwt_nao_emite_aviso_de_chave_curta(self):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            encoded = str(AccessToken())
            AccessToken(encoded)

        self.assertFalse(
            [w for w in captured if issubclass(w.category, InsecureKeyLengthWarning)]
        )


class SecretKeyValidationTests(SimpleTestCase):
    def assert_startup_rejected(self, key, debug):
        result = load_settings_in_subprocess(SECRET_KEY=key, DEBUG=debug)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ImproperlyConfigured', result.stderr)
        self.assertIn('SECRET_KEY fraca', result.stderr)
        # A mensagem de erro informa o tamanho, nunca o valor.
        self.assertNotIn(key, result.stderr)
        self.assertNotIn(key, result.stdout)

    def test_chave_curta_impede_a_inicializacao_em_producao(self):
        self.assert_startup_rejected(secrets.token_hex(8), debug='False')

    def test_chave_curta_impede_a_inicializacao_em_desenvolvimento(self):
        self.assert_startup_rejected(secrets.token_hex(8), debug='True')

    def test_chave_com_poucos_caracteres_distintos_e_recusada(self):
        self.assert_startup_rejected('ab' * 40, debug='True')

    def test_chave_forte_e_aceita_em_producao(self):
        result = load_settings_in_subprocess(SECRET_KEY=secrets.token_urlsafe(64), DEBUG='False')

        self.assertEqual(result.returncode, 0, 'settings recusaram uma chave forte')


class DotenvParsingTests(SimpleTestCase):
    """Documenta a causa raiz e por que a chave é gerada sem caracteres especiais."""

    def read(self, content):
        class IsolatedEnv(environ.Env):
            ENVIRON = {}

        IsolatedEnv.read_env(io.StringIO(content))
        return IsolatedEnv.ENVIRON['SECRET_KEY']

    def test_cerquilha_sem_aspas_trunca_o_valor(self):
        self.assertEqual(self.read('SECRET_KEY=abc#resto-da-chave\n'), 'abc')

    def test_valor_entre_aspas_simples_e_preservado(self):
        self.assertEqual(self.read("SECRET_KEY='abc#resto-da-chave'\n"), 'abc#resto-da-chave')

    def test_chave_no_formato_recomendado_e_lida_integralmente(self):
        key = secrets.token_urlsafe(64)

        self.assertEqual(self.read(f'SECRET_KEY={key}\n'), key)
