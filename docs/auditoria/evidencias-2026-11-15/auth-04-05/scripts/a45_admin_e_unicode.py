"""
AUTH-05 — no processo, banco DESCARTÁVEL a45_lab, tudo dentro de uma transação DESFEITA no fim (o raise fica DENTRO
do atomic): (1) o caminho do Django Admin (formulário de criação e full_clean do model); (2) o EmailValidator com
endereços não ASCII; (3) str.lower() do Python × lower() do PostgreSQL deste banco.
Uso: A45_DB=a45_lab DJANGO_SETTINGS_MODULE=a45_settings python a45_admin_e_unicode.py <saida.json>
"""
import json
import sys
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from django.core.validators import validate_email  # noqa: E402
from django.db import connection, transaction  # noqa: E402

assert settings.DATABASES['default']['NAME'] == 'a45_lab' and settings.DATABASES['default']['PORT'] == '55432'
from accounts.forms import CustomUserCreationForm  # noqa: E402
from accounts.models import User  # noqa: E402
from barbershops.models import Barbershop  # noqa: E402

out = {}


class Desfazer(Exception):
    pass


try:
    with transaction.atomic():
        b = Barbershop.objects.create(nome='Beta Lab', endereco='x', telefone='2', email='c@beta.test',
                                      horario_abertura=time(9), horario_fechamento=time(19))
        User.objects.create_user(email='cliente.b@beta.test', nome='Clara', password='Navalha-Fict-2026!', barbershop=b)
        formulario = []
        for digitado in ['cliente.b@beta.test', 'cliente.b@BETA.TEST', 'Cliente.B@beta.test', 'CLIENTE.B@BETA.TEST', ' cliente.b@beta.test ']:
            with transaction.atomic():
                f = CustomUserCreationForm(data={'email': digitado, 'nome': 'Variante', 'tipo_perfil': 'cliente', 'barbershop': b.pk,
                                                 'password1': 'Navalha-Fict-2026!', 'password2': 'Navalha-Fict-2026!'})
                valido = f.is_valid()
                gravado = f.save().email if valido else None
                formulario.append({'digitado': digitado, 'valido': valido, 'erros': {k: [str(e) for e in v] for k, v in f.errors.items()},
                                   'gravado': gravado})
                transaction.set_rollback(True)
        out['django_admin_formulario_de_criacao'] = formulario
        fc = []
        for digitado in ['Cliente.B@BETA.TEST', 'cliente.b@BETA.TEST']:
            u = User(email=digitado, nome='Variante', barbershop=b)
            u.set_password('Navalha-Fict-2026!')
            try:
                u.full_clean()
                fc.append({'digitado': digitado, 'full_clean': 'passou', 'email_depois_do_clean': u.email})
            except ValidationError as e:
                fc.append({'digitado': digitado, 'full_clean': 'recusou', 'erros': e.message_dict, 'email_depois_do_clean': u.email})
        out['model_full_clean'] = fc
        raise Desfazer
except Desfazer:
    pass
out['usuarios_no_banco_depois_do_rollback'] = User.objects.count()

validador = []
for e in ['joao@exemplo.test', 'joão@exemplo.test', 'cliente@ÁLFA.test', 'cliente@álfa.test', 'cliente@straße.test', 'CLIENTE@STRASSE.TEST',
          '"Quoted Local"@exemplo.test']:
    try:
        validate_email(e)
        validador.append({'email': e, 'aceito_pelo_EmailValidator': True})
    except ValidationError:
        validador.append({'email': e, 'aceito_pelo_EmailValidator': False})
out['email_validator'] = validador

amostras = ['ABC@EXEMPLO.TEST', 'cliente@ÁLFA.test', 'İstanbul@x.test', 'STRAẞE@x.test', 'ǅ@x.test', 'Σ@x.test']
with connection.cursor() as cur:
    cur.execute('select datcollate, datctype, datlocprovider from pg_database where datname = current_database()')
    out['banco'] = dict(zip(['datcollate', 'datctype', 'provider'], cur.fetchone()))
    comparacao = []
    for a in amostras:
        cur.execute('select lower(%s), upper(%s)', [a, a])
        pg_lower, pg_upper = cur.fetchone()
        comparacao.append({'texto': a, 'python_lower': a.lower(), 'pg_lower': pg_lower, 'iguais': a.lower() == pg_lower,
                           'pg_upper': pg_upper, 'python_upper': a.upper()})
out['lower_python_x_postgresql'] = comparacao
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
