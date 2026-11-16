"""
TEN-03 — SIMULAÇÃO DE LABORATÓRIO da Alternativa B (e-mail único por barbearia) SEM alterar o projeto nem criar
migração: dentro de UMA transação desfeita no fim, no banco DESCARTÁVEL t3_lab (PG 18.3, 127.0.0.1:55432), troca-se
a restrição UNIQUE(email) por UNIQUE(email, barbershop_id) e mede-se o que o código ATUAL de login e de recuperação
de senha faz com duas contas de mesmo e-mail em barbearias diferentes.
Uso: DJANGO_SETTINGS_MODULE=t3_lab_settings python t3_simulacao_alt_b.py <saida.json>
"""
import base64
import json
import re
import sys
from datetime import time

import django

django.setup()
from django.conf import settings  # noqa: E402
from django.core import mail  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.test import override_settings  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

assert settings.DATABASES['default']['NAME'] == 't3_lab' and settings.DATABASES['default']['PORT'] == '55432'
from accounts.models import User  # noqa: E402
from barbershops.models import Barbershop  # noqa: E402

S_A, S_B = 'Senha-Alfa-Fict-2026!', 'Senha-Beta-Fict-2026!'
out = {}


class Desfazer(Exception):
    pass


def uid_da_mensagem(m):
    u = re.search(r'^uid: (\S+)$', m.body, re.M).group(1)
    return int(base64.urlsafe_b64decode(u + '=' * (-len(u) % 4)).decode())


try:
    with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'), transaction.atomic():
        with connection.cursor() as cur:
            cur.execute('ALTER TABLE accounts_user DROP CONSTRAINT accounts_user_email_key')
            cur.execute('ALTER TABLE accounts_user ADD CONSTRAINT lab_email_por_barbearia UNIQUE (email, barbershop_id)')
        a = Barbershop.objects.create(nome='Alfa Lab', endereco='x', telefone='1', email='c@alfa.test', horario_abertura=time(9), horario_fechamento=time(19))
        b = Barbershop.objects.create(nome='Beta Lab', endereco='x', telefone='2', email='c@beta.test', horario_abertura=time(9), horario_fechamento=time(19))
        ua = User.objects.create_user(email='mesma.pessoa@exemplo.test', nome='Mesma Pessoa (em A)', password=S_A, tipo_perfil='cliente', barbershop=a)
        ub = User.objects.create_user(email='mesma.pessoa@exemplo.test', nome='Mesma Pessoa (em B)', password=S_B, tipo_perfil='cliente', barbershop=b)
        out['contas'] = {'A': ua.pk, 'B': ub.pk}
        c = APIClient()
        c.raise_request_exception = False
        r = c.post('/api/v1/auth/login/', {'email': 'mesma.pessoa@exemplo.test', 'password': S_A}, format='json')
        out['login_com_a_senha_da_conta_A'] = {'status': r.status_code, 'corpo': r.content.decode()[:120] if r.status_code != 500 else 'HTML "Server Error (500)"'}
        try:
            User.objects.get_by_natural_key('mesma.pessoa@exemplo.test')
            out['get_by_natural_key'] = 'devolveu uma conta'
        except User.MultipleObjectsReturned as e:
            out['get_by_natural_key'] = f'MultipleObjectsReturned: {e}'
        mail.outbox = []
        r = c.post('/api/v1/auth/password/reset/', {'email': 'mesma.pessoa@exemplo.test'}, format='json')
        out['recuperacao_de_senha'] = {'status': r.status_code, 'mensagens': len(mail.outbox),
                                       'conta_que_recebeu_o_token': [uid_da_mensagem(m) for m in mail.outbox],
                                       'observacao': 'filter(email__iexact=...).first() escolhe UMA conta (ordem por nome); a outra fica sem recuperação'}
        # Contas sem barbearia (cadastro público, superusuário): NULL é distinto de NULL numa UNIQUE comum.
        User.objects.create_user(email='sem.tenant@exemplo.test', nome='Sem Tenant 1', password=S_A)
        try:
            with transaction.atomic():
                User.objects.create_user(email='sem.tenant@exemplo.test', nome='Sem Tenant 2', password=S_B)
            out['duas_contas_sem_barbearia_com_o_mesmo_email'] = 'ACEITAS (UNIQUE comum trata NULL como distinto; exigiria NULLS NOT DISTINCT)'
        except Exception as e:  # noqa: BLE001
            out['duas_contas_sem_barbearia_com_o_mesmo_email'] = f'recusadas: {type(e).__name__}'
        with connection.cursor() as cur:
            cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
            cur.execute('ALTER TABLE accounts_user DROP CONSTRAINT lab_email_por_barbearia')
            try:
                with transaction.atomic():
                    cur.execute('ALTER TABLE accounts_user ADD CONSTRAINT lab_email_por_barbearia UNIQUE NULLS NOT DISTINCT (email, barbershop_id)')
                out['restricao_nulls_not_distinct_com_as_duas_contas_sem_barbearia'] = 'criada (inesperado)'
            except Exception as e:  # noqa: BLE001
                out['restricao_nulls_not_distinct_com_as_duas_contas_sem_barbearia'] = 'recusada pelo banco: ' + str(e).splitlines()[0]
        raise Desfazer  # dentro do atomic(): desfaz DDL e dados
except Desfazer:
    pass
except Exception as e:  # noqa: BLE001
    out['erro_inesperado'] = repr(e)
with connection.cursor() as cur:
    cur.execute("select conname from pg_constraint where conrelid = 'accounts_user'::regclass and contype = 'u'")
    out['restricoes_unique_depois_do_rollback'] = [r[0] for r in cur.fetchall()]
out['usuarios_no_banco_depois_do_rollback'] = User.objects.count()
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
