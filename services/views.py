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
        # Filtro por status ativo/inativo:
        # - Sem parâmetro (público) → apenas ativos
        # - ativo=true → apenas ativos
        # - ativo=false → apenas inativos
        # - ativo=all (apenas admin) → todos (sem filtro)
        ativo_param = self.request.query_params.get('ativo')
        user = self.request.user

        # Para operações de escrita (UPDATE, DELETE), superuser deve poder
        # acessar serviços inativos para reativar ou confirmar exclusão.
        is_write_operation = self.action in ['update', 'partial_update', 'destroy']

        if ativo_param == 'all':
            # Apenas admins podem ver inativos via ativo=all
            if user.is_authenticated and (user.is_superuser or user.tipo_perfil == 'admin'):
                # Admin explícito: retorna todos, sem filtro por ativo
                pass
            else:
                # Não-admins: ignora ativo=all e usa padrão (apenas ativos)
                queryset = queryset.filter(ativo=True)
        elif ativo_param == 'false':
            # Apenas admins podem filtrar inativos
            if user.is_authenticated and (user.is_superuser or user.tipo_perfil == 'admin'):
                queryset = queryset.filter(ativo=False)
            else:
                # Não-admins não podem ver inativos
                queryset = queryset.filter(ativo=True)
        else:
            # ativo=true ou parâmetro ausente (padrão público)
            # Mas para operações de escrita de superuser, não filtramos por ativo
            # para permitir reativação e exclusão de inativos
            if is_write_operation and user.is_authenticated and user.is_superuser:
                pass  # Superuser em operação de escrita vê todos
            else:
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
