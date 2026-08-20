"""
Mixins reutilizáveis pelos ViewSets dos apps de negócio.
"""


class TenantScopedQuerysetMixin:
    """
    Aplica o isolamento multi-tenant automaticamente em qualquer ViewSet
    cujo modelo tenha um campo `barbershop`:

    - Restringe o queryset (list/retrieve/update/delete) à barbearia do
      usuário autenticado.
    - Preenche automaticamente o campo `barbershop` ao criar um registro,
      então o cliente da API nunca precisa (e não consegue) informar
      esse campo manualmente.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.barbershop_id:
            queryset = queryset.filter(barbershop_id=user.barbershop_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(barbershop_id=self.request.user.barbershop_id)
