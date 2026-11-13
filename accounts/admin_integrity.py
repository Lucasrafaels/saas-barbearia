"""
Integridade dos administradores de cada barbearia (BUS-01).

Fonte única das duas regras, usada pela API, pelo Django Admin e pelo modelo:

1. Ninguém altera o próprio perfil, desativa ou exclui a própria conta.
   Depende de quem executa a ação, então é verificada pelas interfaces que
   conhecem o usuário logado (API e Django Admin), com check_self_change().

2. Uma barbearia que tem administrador ativo nunca fica sem nenhum.
   Não depende de quem executa, nem mesmo do superusuário. É imposta pelo
   próprio modelo (User.save, User.delete, UserQuerySet.update e
   UserQuerySet.delete) com preserving_active_admins(). Isso cobre exclusão,
   desativação, rebaixamento e transferência para outra barbearia, unitária
   ou em lote. As interfaces só antecipam a mensagem com check_admin_removal().

Fica de fora apenas o que não passa pelo ORM (SQL direto no banco).
"""
from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import transaction

# Campos cuja alteração pode tirar alguém da condição de admin ativo de uma
# barbearia. `save(update_fields=...)` sem nenhum deles (ex.: last_login,
# password) não passa pela verificação.
GUARDED_FIELDS = frozenset({'tipo_perfil', 'is_active', 'barbershop', 'barbershop_id'})

LAST_ADMIN_MESSAGE = (
    'Esta operação deixaria a barbearia sem nenhum administrador ativo. '
    'Crie ou ative outro administrador antes de remover, desativar ou rebaixar este.'
)
SELF_ROLE_MESSAGE = 'Você não pode alterar o próprio perfil de acesso.'
SELF_DEACTIVATE_MESSAGE = 'Você não pode desativar a própria conta.'
SELF_DELETE_MESSAGE = 'Você não pode excluir a própria conta.'

ADMIN = 'admin'


class AdminIntegrityError(ValidationError):
    """Violação de uma regra de integridade dos administradores."""


def _users():
    # Import tardio: accounts.models importa este módulo.
    from .models import User

    return User._base_manager


def _active_admins():
    return _users().filter(tipo_perfil=ADMIN, is_active=True)


def lock_active_admins(barbershop_ids):
    """Trava os admins ativos das barbearias e devolve as que têm algum.

    SELECT ... FOR UPDATE, sempre na ordem do pk: operações simultâneas sobre a
    mesma barbearia ficam em fila, e a seguinte já enxerga o resultado da
    anterior. Precisa rodar dentro de uma transação.
    """
    ids = {pk for pk in barbershop_ids if pk is not None}
    if not ids:
        return set()
    return set(
        _active_admins()
        .select_for_update()
        .filter(barbershop_id__in=ids)
        .order_by('pk')
        .values_list('barbershop_id', flat=True)
    )


def active_admin_barbershop(user_pk):
    """Barbearia da qual o usuário é admin ativo hoje (no banco), ou None."""
    return _active_admins().filter(pk=user_pk).values_list('barbershop_id', flat=True).first()


@contextmanager
def preserving_active_admins(barbershop_ids):
    """Executa o bloco garantindo que as barbearias não percam o último admin ativo.

    Trava os admins ativos antes do bloco e confere o resultado depois dele, na
    mesma transação. Se alguma barbearia que tinha admin ativo ficar sem
    nenhum, levanta AdminIntegrityError e a transação é desfeita.
    """
    with transaction.atomic():
        protected = lock_active_admins(barbershop_ids)
        yield
        if not protected:
            return
        remaining = set(
            _active_admins().filter(barbershop_id__in=protected).values_list('barbershop_id', flat=True)
        )
        if protected - remaining:
            raise AdminIntegrityError(LAST_ADMIN_MESSAGE, code='last_active_admin')


def check_admin_removal(user_pks):
    """Antecipa, sem travar, se remover esses usuários deixaria alguma barbearia sem admin.

    Serve para as interfaces mostrarem o erro antes de gravar. A garantia
    definitiva, inclusive sob concorrência, é preserving_active_admins().
    """
    pks = set(user_pks)
    affected = set(_active_admins().filter(pk__in=pks).exclude(barbershop=None)
                   .values_list('barbershop_id', flat=True))
    for barbershop_id in affected:
        if not _active_admins().filter(barbershop_id=barbershop_id).exclude(pk__in=pks).exists():
            raise AdminIntegrityError(LAST_ADMIN_MESSAGE, code='last_active_admin')


def check_self_change(actor, target, *, tipo_perfil=None, is_active=None, deleting=False):
    """Recusa que `actor` altere o próprio perfil, se desative ou se exclua."""
    if actor is None or actor.pk is None or actor.pk != target.pk:
        return
    if deleting:
        raise AdminIntegrityError(SELF_DELETE_MESSAGE, code='self_delete')
    errors = {}
    if tipo_perfil is not None and tipo_perfil != target.tipo_perfil:
        errors['tipo_perfil'] = SELF_ROLE_MESSAGE
    if is_active is False:
        errors['is_active'] = SELF_DEACTIVATE_MESSAGE
    if errors:
        raise AdminIntegrityError(errors)
