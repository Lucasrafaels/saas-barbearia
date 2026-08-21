from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'admin'

class IsBarberRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'barbeiro'

class IsClientRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_perfil == 'cliente'
