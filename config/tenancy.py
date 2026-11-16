"""
Escopo de tenant (barbearia) para referências entre registros (TEN-01).

Toda referência a outro registro que chega numa requisição, seja num campo
relacional de serializer, seja num filtro de listagem, é resolvida dentro da
barbearia do usuário autenticado. A condição de tenant faz parte da própria
consulta:

- o registro de outra barbearia nunca é lido;
- um ID de outra barbearia recebe exatamente a mesma resposta de um ID
  inexistente, sem oráculo de existência (SEC-10);
- os formulários e as opções que o DRF ou o django-filter montarem a partir
  desses querysets só listam registros do próprio tenant.

As checagens de tenant que já existiam (``get_queryset()`` das views,
``validate()`` dos serializers e ``clean()`` dos models) continuam valendo
como defesa em profundidade.
"""
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from rest_framework import serializers


class _TodasAsBarbearias:
    """Escopo sem restrição, reservado ao superusuário (operador da plataforma)."""

    def __repr__(self):
        return 'TODAS_AS_BARBEARIAS'


TODAS_AS_BARBEARIAS = _TodasAsBarbearias()


def barbearia_do_pedido(request, instancia=None):
    """
    Barbearia cujos registros o pedido pode referenciar.

    Devolve o ID da barbearia, ``None`` (nenhum registro) ou
    ``TODAS_AS_BARBEARIAS``. O escopo vem sempre do usuário autenticado,
    nunca de IDs enviados no corpo ou na URL.

    - Sem usuário autenticado: nenhuma.
    - Usuário comum: a própria barbearia. Sem barbearia (por exemplo, a conta
      recém-criada no cadastro público), nenhuma: a falta de contexto não
      amplia o acesso.
    - Superusuário: é a exceção explícita, como em
      ``TenantScopedQuerysetMixin``, e a decisão vem de ``is_superuser``,
      nunca de um ``barbershop_id`` vazio. Ao editar um registro, vale a
      barbearia desse registro, que a view já autorizou. Sem registro, vale a
      própria barbearia, se houver; senão, todas. Criar recursos de tenant sem
      contexto continua bloqueado nas views.
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    if user.is_superuser:
        barbearia_da_instancia = getattr(instancia, 'barbershop_id', None)
        if barbearia_da_instancia:
            return barbearia_da_instancia
        return user.barbershop_id or TODAS_AS_BARBEARIAS
    return user.barbershop_id or None


def campo_de_tenant(model):
    """Nome do lookup que liga o model à barbearia. Falha fechado se não houver."""
    if model._meta.label_lower == 'barbershops.barbershop':
        return 'pk'
    try:
        model._meta.get_field('barbershop')
    except FieldDoesNotExist as error:
        raise ImproperlyConfigured(
            f'{model._meta.label} não tem barbearia: defina como limitá-lo ao tenant '
            'antes de usá-lo num campo relacional ou num filtro.'
        ) from error
    return 'barbershop_id'


def limitar_a_barbearia(queryset, barbearia):
    """Restringe o queryset ao escopo devolvido por ``barbearia_do_pedido``."""
    if barbearia is TODAS_AS_BARBEARIAS:
        return queryset
    if barbearia is None:
        return queryset.none()
    return queryset.filter(**{campo_de_tenant(queryset.model): barbearia})


class TenantScopedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    ``PrimaryKeyRelatedField`` cujo queryset é limitado à barbearia do pedido.

    Usado como ``serializer_related_field`` dos ``ModelSerializer`` que recebem
    referências a registros de tenant. Assim, os campos gerados a partir do
    model mantêm rótulo, validadores e ``limit_choices_to``, e só ganham o
    escopo. Sem requisição no contexto, o queryset fica vazio (falha fechado).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # O DRF dispensa a checagem de "queryset obrigatório" quando a subclasse
        # sobrescreve get_queryset(). Ela é refeita aqui: um campo gravável sem
        # queryset aceitaria qualquer coisa.
        assert self.queryset is not None or self.read_only, (
            'TenantScopedPrimaryKeyRelatedField gravável precisa de um queryset.'
        )

    def _serializer(self):
        pai = self.parent
        while pai is not None and not isinstance(pai, serializers.BaseSerializer):
            pai = pai.parent
        return pai

    def get_queryset(self):
        queryset = super().get_queryset()
        serializer = self._serializer()
        instancia = getattr(serializer, 'instance', None)
        if not isinstance(instancia, models.Model):
            # Listas (many=True) e serializers sem instância não têm registro em edição.
            instancia = None
        return limitar_a_barbearia(queryset, barbearia_do_pedido(self.context.get('request'), instancia))
