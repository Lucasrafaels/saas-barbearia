"""
Views do app barbershops.
"""
from rest_framework import permissions, viewsets

from core.mixins import TenantScopedQuerysetMixin
from core.permissions import IsAdminRole
from .models import Barber, Barbershop
from .serializers import BarberSerializer, BarbershopSerializer


class BarbershopViewSet(viewsets.ModelViewSet):
    """
    Gestão da barbearia (o tenant). Um usuário comum só enxerga a
    própria barbearia; superusuários (equipe interna da plataforma)
    enxergam todas — útil para suporte/onboarding de novos clientes.
    """
    queryset = Barbershop.objects.all()
    serializer_class = BarbershopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        return super().get_queryset().filter(id=user.barbershop_id)

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class BarberViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Gestão dos barbeiros da barbearia do usuário autenticado. Leitura
    liberada para qualquer usuário autenticado da barbearia (ex.: um
    cliente precisa ver a lista de barbeiros para agendar); escrita
    restrita a administradores.
    """
    queryset = Barber.objects.select_related('user', 'barbershop').all()
    serializer_class = BarberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]
