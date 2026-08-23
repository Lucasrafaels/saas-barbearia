"""
Views do app appointments.
"""
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from barbershops.models import Barber
from config.mixins import TenantScopedQuerysetMixin
from services.models import Service

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
        elif user.is_barbeiro:
            queryset = queryset.filter(barbeiro=user.perfil_barbeiro)
        return queryset

    def perform_create(self, serializer):
        extra = {'barbershop_id': self.request.user.barbershop_id}
        # Um cliente só pode marcar horário para si mesmo; administradores
        # e barbeiros podem informar o cliente explicitamente (ex.: ao
        # registrar um agendamento feito por telefone).
        if self.request.user.is_cliente:
            extra['cliente'] = self.request.user
        elif self.request.user.is_barbeiro:
            extra['barbeiro'] = self.request.user.perfil_barbeiro
        serializer.save(**extra)

    def perform_update(self, serializer):
        if self.request.user.is_cliente:
            # Defesa em profundidade: a validação rejeita a troca e este
            # reforço garante que o campo nunca seja persistido diferente.
            serializer.save(cliente=self.request.user)
            return
        serializer.save()

    @action(detail=False, methods=['get'], url_path='available-slots')
    def available_slots(self, request):
        """
        GET /api/v1/appointments/available-slots/?barbeiro=7&servico=4&data=2026-08-25

        Retorna os horários (HH:MM) em que o barbeiro ainda pode iniciar um
        atendimento do serviço informado na data informada: slots gerados a
        partir da abertura da barbearia até caber mais um serviço antes do
        fechamento, com passo igual à duração do serviço, excluindo os que
        conflitam com agendamentos existentes (status != cancelado).

        Todos os cálculos usam a timezone local do projeto (TIME_ZONE),
        consistente com as validações de horário de funcionamento do model.
        """
        user = request.user
        if user.barbershop_id is None:
            return Response(
                {'detail': 'Usuário sem barbearia vinculada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        barbeiro_id = request.query_params.get('barbeiro')
        servico_id = request.query_params.get('servico')
        data_param = request.query_params.get('data')
        faltando = [
            nome for nome, valor in (
                ('barbeiro', barbeiro_id), ('servico', servico_id), ('data', data_param),
            ) if not valor
        ]
        if faltando:
            return Response(
                {'detail': f'Parâmetros obrigatórios ausentes: {", ".join(faltando)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            barbeiro = Barber.objects.get(id=barbeiro_id)
        except (Barber.DoesNotExist, ValueError):
            return Response({'detail': 'Barbeiro não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            servico = Service.objects.get(id=servico_id)
        except (Service.DoesNotExist, ValueError):
            return Response({'detail': 'Serviço não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            data = datetime.strptime(data_param, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Data inválida. Use o formato YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Escopo multi-tenant: barbeiro e serviço devem pertencer à barbearia
        # do usuário autenticado.
        if barbeiro.barbershop_id != user.barbershop_id or servico.barbershop_id != user.barbershop_id:
            return Response({'detail': 'Recurso não pertence à sua barbearia.'}, status=status.HTTP_403_FORBIDDEN)

        duracao = timedelta(minutes=servico.duracao)

        inicio = timezone.make_aware(datetime.combine(data, barbeiro.barbershop.horario_abertura))
        limite = timezone.make_aware(datetime.combine(data, barbeiro.barbershop.horario_fechamento)) - duracao

        agendamentos = Appointment.objects.filter(
            barbeiro=barbeiro,
            data_hora__date=data,
        ).exclude(status=Appointment.Status.CANCELADO).values_list('data_hora', flat=True)

        ocupados = [
            (timezone.localtime(inicio_agendado), timezone.localtime(inicio_agendado) + duracao)
            for inicio_agendado in agendamentos
        ]

        slots = []
        slot_atual = inicio
        while slot_atual <= limite:
            fim_slot = slot_atual + duracao
            conflita = any(inicio_ocupado < fim_slot and slot_atual < fim_ocupado
                           for inicio_ocupado, fim_ocupado in ocupados)
            if not conflita:
                slots.append(slot_atual.strftime('%H:%M'))
            slot_atual += duracao

        return Response({'data': data.isoformat(), 'slots': slots})
