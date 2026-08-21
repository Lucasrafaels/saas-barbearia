from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'admin'


class IsSelfOrAdmin(BasePermission):
    """Permite que um usuário acesse somente o próprio cadastro, salvo admins."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user.is_authenticated
            and (user.is_superuser or user.tipo_perfil == 'admin' or user.pk == obj.pk)
        )


class IsBarberRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'barbeiro'

class IsClientRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'cliente'
