"""
Views do app appointments.
"""
from rest_framework import permissions, viewsets

from config.mixins import TenantScopedQuerysetMixin
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Gestão de agendamentos da barbearia do usuário autenticado.
    Clientes só enxergam os próprios agendamentos; administradores e
    barbeiros enxergam todos os agendamentos da barbearia.
    """
    queryset = Appointment.objects.select_related(
        'cliente', 'barbeiro__user', 'servico', 'barbershop'
    ).all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'barbeiro', 'servico']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_cliente:
            queryset = queryset.filter(cliente=user)
        return queryset

    def perform_create(self, serializer):
        extra = {'barbershop_id': self.request.user.barbershop_id}
        # Um cliente só pode marcar horário para si mesmo; administradores
        # e barbeiros podem informar o cliente explicitamente (ex.: ao
        # registrar um agendamento feito por telefone).
        if self.request.user.is_cliente:
            extra['cliente'] = self.request.user
        serializer.save(**extra)

    def perform_update(self, serializer):
        if self.request.user.is_cliente:
            # Defesa em profundidade: a validação rejeita a troca e este
            # reforço garante que o campo nunca seja persistido diferente.
            serializer.save(cliente=self.request.user)
            return
        serializer.save()
