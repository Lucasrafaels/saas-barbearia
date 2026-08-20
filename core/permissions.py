"""
Permissões customizadas, reutilizadas pelos ViewSets dos apps de negócio
para controle de acesso baseado no tipo de perfil do usuário
(accounts.User.tipo_perfil).
"""
from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    """Permite acesso apenas a usuários com tipo_perfil='admin'."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )


class IsAdminOrBarbeiro(permissions.BasePermission):
    """Permite acesso a administradores e barbeiros da barbearia."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin or request.user.is_barbeiro)
        )


class IsSameBarbershop(permissions.BasePermission):
    """
    Permissão em nível de objeto: garante que o usuário só acesse/edite
    registros pertencentes à mesma barbearia à qual está vinculado.
    Útil como camada extra de segurança em retrieve/update/delete,
    complementando o filtro de queryset (que cobre list/create).
    """

    def has_object_permission(self, request, view, obj):
        barbershop_id = getattr(obj, 'barbershop_id', None)
        return barbershop_id is not None and barbershop_id == request.user.barbershop_id
