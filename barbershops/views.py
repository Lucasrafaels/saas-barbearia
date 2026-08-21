"""
Views do app barbershops.
"""
from rest_framework import permissions, viewsets

from config.mixins import TenantScopedQuerysetMixin
from config.permissions import IsAdminRole
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
        # Criar é o fluxo de onboarding: qualquer usuário autenticado sem
        # barbearia ainda pode criar a sua (e vira admin dela, ver
        # perform_create). Destruir continua restrito à equipe da
        # plataforma (staff do Django admin).
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        barbershop = serializer.save()
        user = self.request.user
        # O usuário que cria a barbearia passa a ser o admin dela — sem
        # isso, a barbearia nunca fica associada a ninguém (bug original).
        if not user.barbershop_id:
            user.barbershop = barbershop
            user.tipo_perfil = user.TipoPerfil.ADMIN
            user.save(update_fields=['barbershop', 'tipo_perfil'])


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

    def perform_create(self, serializer):
        serializer.save(barbershop_id=self.request.user.barbershop_id)
