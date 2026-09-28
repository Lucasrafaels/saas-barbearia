"""
Views do app services.
"""
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, APIException

from config.mixins import TenantScopedQuerysetMixin
from config.permissions import IsAdminRole
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

    def get_queryset(self):
        queryset = super().get_queryset()
        # Recursos desativados preservam o histórico, mas não voltam a ser
        # oferecidos a clientes por padrão. Administradores podem consultar
        # explicitamente ?ativo=false para auditoria/restauração manual.
        if self.action == 'list' and 'ativo' not in self.request.query_params:
            queryset = queryset.filter(ativo=True)
        return queryset

    def perform_create(self, serializer):
        # `barbershop` é read_only no serializer; precisa ser preenchido
        # aqui a partir do usuário autenticado (mesmo padrão do
        # AppointmentViewSet.perform_create).
        if self.request.user.barbershop_id is None:
            raise PermissionDenied(
                'Selecione um contexto de barbearia antes de criar um serviço.'
            )
        serializer.save(barbershop_id=self.request.user.barbershop_id)

    def perform_destroy(self, instance):
        # Soft delete: marca como inativo e registra a exclusão para preservar histórico
        instance.ativo = False
        instance.deleted_at = timezone.now()
        instance.deleted_by = self.request.user
        instance.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
