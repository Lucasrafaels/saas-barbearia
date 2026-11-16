"""accounts.0006: contas FICTÍCIAS em grafias que a regra normaliza sem colisão, gravadas com o CÓDIGO ANTERIOR
(User.save não normalizava). Uso: M_DB=m_valido DJANGO_SETTINGS_MODULE=m_settings python m_dados_validos.py"""
import django

django.setup()
from django.conf import settings  # noqa: E402

assert settings.DATABASES['default']['NAME'] == 'm_valido'
from accounts.models import User  # noqa: E402

for email in ['ja.normalizado@exemplo.test', 'Pessoa.Dois@exemplo.test', 'novo.3@EXEMPLO.TEST', 'TUDO@MAIUSCULO.TEST',
              ' espaco.inicio@exemplo.test', 'espaco.fim@exemplo.test\t']:
    u = User(email=email, nome='Conta Antiga', tipo_perfil='cliente')
    u.set_unusable_password()
    u.save()
print('contas:', User.objects.count())
