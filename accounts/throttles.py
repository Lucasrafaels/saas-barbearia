"""
Limites de tentativas das operações que consultam a unicidade do e-mail (TEN-03, mitigação D).

O e-mail é único em toda a plataforma e é o login (seção 26 do relatório de
auditoria). Por isso, o cadastro público, a criação de usuários e a troca de
e-mail respondem de um jeito quando o e-mail já existe, em qualquer barbearia,
e de outro quando ele está livre. Estes limites só reduzem a velocidade da
sondagem automatizada. **Não eliminam o oráculo:** abaixo do limite, a resposta
continua revelando a existência. A correção definitiva planejada é a C3
(confirmação por e-mail e convites).

Regras:
- A chave é sempre quem pede: a conta autenticada ou, para o anônimo, a origem
  (o mesmo `get_ident` dos limites que já existiam). Nunca é o e-mail nem a
  conta-alvo. Assim, um terceiro não consegue gastar a cota de outra pessoa nem
  impedir que ela use a própria conta.
- Cada operação tem escopos próprios, separados dos de login e recuperação de
  senha, que não mudaram.
- As taxas ficam em `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`
  (`config/settings.py`), como as demais.
"""
from rest_framework.throttling import SimpleRateThrottle

from .emails import forma_canonica


class LimitePorSolicitante(SimpleRateThrottle):
    """
    Igual ao `ScopedRateThrottle`, mas com o escopo fixo na classe.

    O `ScopedRateThrottle` lê o escopo de `view.throttle_scope` e por isso só
    admite um limite por view. Aqui, cada classe tem o seu, e uma view pode
    ter vários: um por hora e um por dia.
    """

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class CadastroPublicoPorDiaThrottle(LimitePorSolicitante):
    """Cadastro público: soma-se ao limite por hora do escopo `register`, que já existia."""

    scope = 'register_day'


class CriacaoDeUsuarioPorHoraThrottle(LimitePorSolicitante):
    """`POST /users/`, por conta. Só administradores chegam aqui: a permissão é checada antes."""

    scope = 'user_create'


class CriacaoDeUsuarioPorDiaThrottle(LimitePorSolicitante):
    scope = 'user_create_day'


class TrocaDeEmailPorHoraThrottle(LimitePorSolicitante):
    """`PATCH`/`PUT /users/{id}/` que tenta gravar outro e-mail, por conta de quem pede."""

    scope = 'email_change'


class TrocaDeEmailPorDiaThrottle(LimitePorSolicitante):
    scope = 'email_change_day'


LIMITES_DE_CRIACAO_DE_USUARIO = (CriacaoDeUsuarioPorHoraThrottle, CriacaoDeUsuarioPorDiaThrottle)
LIMITES_DE_TROCA_DE_EMAIL = (TrocaDeEmailPorHoraThrottle, TrocaDeEmailPorDiaThrottle)


def tenta_trocar_email(dados, conta):
    """
    Diz se o pedido tenta gravar na conta um e-mail diferente do atual.

    Só esses pedidos consultam a unicidade de forma útil para a sondagem.
    Reenviar o próprio e-mail não conta. É o caso das telas "Minha conta" e
    "Clientes", que sempre mandam nome e e-mail juntos. Editar só outros campos
    também não conta. A comparação segue o `EmailField` do DRF, que corta os
    espaços das pontas antes de validar.

    `conta` já foi obtida por `get_object()`, com o escopo e a permissão do
    solicitante. Por isso, a comparação usa apenas um e-mail que ele já pode ver.

    AUTH-05: a comparação usa a forma canônica (accounts.emails), a mesma que o
    serializer grava. Reenviar o próprio e-mail em outra caixa não troca nada e
    não conta. Um texto fora da regra, que o serializer recusa, continua
    contando como antes.
    """
    if not hasattr(dados, 'get') or 'email' not in dados:
        return False
    valor = dados.get('email')
    if isinstance(valor, str):
        canonico = forma_canonica(valor)
        valor = canonico if canonico is not None else valor.strip()
    return valor != conta.email
