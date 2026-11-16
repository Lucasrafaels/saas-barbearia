"""
Regra única do e-mail de login (AUTH-04 e AUTH-05; seções 28 a 31 do relatório de auditoria).

O e-mail identifica a conta em toda a plataforma. A forma canônica é:

1. tirar os espaços externos com a semântica de `str.strip()`, a mesma que o DRF,
   os formulários do Django e o `normalize_email` já usavam;
2. exigir que o restante tenha **só ASCII imprimível**, de U+0021 a U+007E, sem
   espaços nem controles. A checagem vem **antes** da conversão: caracteres
   Unicode que viram ASCII ao converter (por exemplo, o sinal de Kelvin U+212A
   vira "k") são recusados, e não aceitos por acaso;
3. converter o endereço inteiro para minúsculas.

Por que só ASCII (seção 30): com `pt_BR.UTF-8`, o `lower()` do PostgreSQL e o
do Python divergem em 56 caracteres Unicode, e o `EmailValidator` aceita
caracteres invisíveis no domínio. Na faixa ASCII, as duas normalizações são
idênticas, o que foi medido em todos os pontos de código. Isso permite que o
banco garanta a mesma regra com
`CHECK (email = lower(email) AND email ~ '^[!-~]+$')` e `UNIQUE (LOWER(email))`
(migração `accounts.0006`). O frontend já só aceitava ASCII. Domínios
internacionais continuam aceitos na forma punycode (`xn--…`).

Não há conversão de tipo: um valor que não é `str` não tem forma canônica.
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

# U+0021..U+007E. A mesma faixa vai para a restrição CHECK do banco (accounts.0006).
FAIXA_PERMITIDA = re.compile(r'[!-~]+')
EXPRESSAO_SQL_DA_FAIXA = r'^[!-~]+$'

# Os nomes das restrições que garantem a unicidade do e-mail no banco. O primeiro
# é o que o PostgreSQL deu ao `unique=True` do campo (accounts.0001); o segundo é
# a unicidade funcional criada em accounts.0006.
RESTRICAO_UNIQUE_DO_CAMPO = 'accounts_user_email_key'
RESTRICAO_UNIQUE_LOWER = 'accounts_user_email_lower_unico'
RESTRICAO_CHECK = 'accounts_user_email_normalizado'


def forma_canonica(valor):
    """
    Devolve a forma canônica do e-mail, ou `None` quando o valor não cabe na regra.

    Não converte tipos e não valida a sintaxe do e-mail, que continua a cargo do
    `EmailValidator` do projeto. Só decide a forma.
    """
    if not isinstance(valor, str):
        return None
    sem_espacos_externos = valor.strip()
    if not FAIXA_PERMITIDA.fullmatch(sem_espacos_externos):
        return None
    return sem_espacos_externos.lower()


def normalizar_email(valor):
    """Forma canônica para gravar. Se o valor não couber na regra, levanta `ValidationError` ('invalid')."""
    canonico = forma_canonica(valor)
    if canonico is None:
        raise ValidationError(EmailValidator.message, code='invalid')
    return canonico


def e_violacao_da_unicidade_do_email(erro):
    """
    Diz se um `IntegrityError` veio de uma das restrições de unicidade do e-mail.

    Qualquer outro erro de integridade, inclusive o CHECK de forma canônica, que
    só falha num caminho que não normalizou, não é "e-mail duplicado" e não pode
    virar essa mensagem. No PostgreSQL, o nome vem do diagnóstico do driver. No
    SQLite dos testes, vem do texto padrão do erro.
    """
    causa = getattr(erro, '__cause__', None)
    nome = getattr(getattr(causa, 'diag', None), 'constraint_name', None)
    if nome is not None:
        return nome in (RESTRICAO_UNIQUE_DO_CAMPO, RESTRICAO_UNIQUE_LOWER)
    texto = str(erro)
    return texto in (
        'UNIQUE constraint failed: accounts_user.email',
        f"UNIQUE constraint failed: index '{RESTRICAO_UNIQUE_LOWER}'",
    )
