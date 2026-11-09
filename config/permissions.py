from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.tipo_perfil == 'admin')
        )


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
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.tipo_perfil != 'barbeiro':
            return False
        # Verify active Barber profile exists in the user's barbershop
        from barbershops.models import Barber
        return Barber.objects.filter(
            user=request.user,
            barbershop_id=request.user.barbershop_id,
            ativo=True
        ).exists()

class IsClientRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'cliente'
