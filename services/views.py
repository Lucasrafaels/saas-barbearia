"""
Views do app services.
"""
from rest_framework import permissions, viewsets

from core.mixins import TenantScopedQuerysetMixin
from core.permissions import IsAdminRole
from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Gestão dos serviços oferecidos pela barbearia. Leitura liberada
    para qualquer usuário autenticado da barbearia (o cliente precisa
    ver os serviços para agendar); escrita restrita a administradores.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['ativo']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]
