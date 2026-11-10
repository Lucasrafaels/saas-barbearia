"""
Views do app appointments.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from barbershops.models import Barber
from config.mixins import TenantScopedQuerysetMixin
from config.permissions import IsAdminRole, IsBarberRole
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

    def get_permissions(self):
        # Clientes podem criar e cancelar o próprio horário, mas não podem
        # alterar status (confirmado/realizado). Essas transições ficam com
        # administrador e barbeiro; o queryset continua impondo o escopo.
        if self.action in ['update', 'partial_update']:
            if self.request.user.is_cliente:
                # Clientes podem atualizar seus próprios agendamentos (reagendamento ou cancelamento)
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsAdminOrBarberRole()]
        if self.action == 'destroy':
            # O DELETE é um cancelamento lógico. O queryset já limita o
            # cliente ao próprio agendamento.damento; barbeiros continuam sem poder
            # cancelar horários de clientes arbitrariamente.
            if self.request.user.is_cliente:
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Superuser pode ver todos os agendamentos independentemente do filtro
        # Para operações de escrita (UPDATE, DELETE), superuser vê todos
        # independentemente do status para permitir reativação/exclusão
        is_write_operation = self.action in ['update', 'partial_update', 'destroy']
        if user.is_authenticated and user.is_superuser:
            if is_write_operation:
                return queryset  # Todos
            # Para leitura, aplicar filtros normais baseados no papel
            # (superuser age como admin da plataforma)

        if user.is_cliente:
            queryset = queryset.filter(cliente=user)
        elif user.is_barbeiro:
            barbeiro = getattr(user, 'perfil_barbeiro', None)
            if (
                barbeiro is None
                or not barbeiro.ativo
                or barbeiro.barbershop_id != user.barbershop_id
            ):
                return queryset.none()
            queryset = queryset.filter(barbeiro=barbeiro)
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.barbershop_id:
            raise PermissionDenied('Usuário sem barbearia vinculada.')
        extra = {'barbershop_id': self.request.user.barbershop_id}
        # Um cliente só pode marcar horário para si mesmo; administradores
        # e barbeiros podem informar o cliente explicitamente (ex.: ao
        # registrar um agendamento feito por telefone).
        if self.request.user.is_cliente:
            extra['cliente'] = self.request.user
        elif self.request.user.is_barbeiro:
            barbeiro = getattr(self.request.user, 'perfil_barbeiro', None)
            if (
                barbeiro is None
                or not barbeiro.ativo
                or barbeiro.barbershop_id != self.request.user.barbershop_id
            ):
                raise PermissionDenied('Perfil profissional de barbeiro ativo não encontrado.')
            extra['barbeiro'] = barbeiro
        serializer.save(**extra)

    def perform_update(self, serializer):
        if self.request.user.is_cliente:
            # Defesa em profundidade: a validação rejeita a troca e este
            # reforço garante que o campo nunca seja persistido diferente.
            serializer.save(cliente=self.request.user)
            return
        serializer.save()

    def perform_destroy(self, instance):
        # DELETE representa o cancelamento do agendamento, preservando o histórico.
        # Aplica a mesma máquina de estados: só permite cancelar se o status atual
        # permitir a transição para cancelado (agendado ou confirmado).
        # Não permite cancelar agendamentos realizados ou já cancelados.
        if instance.status in [Appointment.Status.AGENDADO, Appointment.Status.CONFIRMADO]:
            instance.status = Appointment.Status.CANCELADO
            instance.save(update_fields=['status', 'updated_at'])
        elif instance.status == Appointment.Status.CANCELADO:
            # Já cancelado - operação idempotente, retorna sucesso sem modificar
            pass
        else:
            # REALIZADO não pode ser cancelado
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'detail': f'Não é possível cancelar um agendamento com status {instance.get_status_display()}.'
            })

    @action(detail=False, methods=['get'], url_path='available-slots')
    def available_slots(self, request):
        """
        GET /api/v1/appointments/available-slots/?barbeiro=7&servico=4&data=2026-08-25[&exclude_appointment_id=123]

        Retorna os horários (HH:MM) em que o barbeiro ainda pode iniciar um
        atendimento do serviço informado na data informada: slots gerados a
        partir da abertura da barbearia até caber mais um serviço antes do
        fechamento, com passo igual à duração do serviço, excluindo os que
        conflitam com agendamentos existentes (status != cancelado).

        Parâmetro opcional `exclude_appointment_id`: durante um reagendamento,
        informe o ID do agendamento original para que ele não seja considerado
        como horário ocupado. O backend valida:
        - Se o agendamento existe.
        - Se pertence à barbearia do usuário.
        - Se o usuário tem permissão para reagendá-lo.
        - Se o status permite reagendamento (agendado ou confirmado).
        - Se não está cancelado ou realizado.

        Todos os cálculos usam a timezone local do projeto (TIME_ZONE),
        consistente com as validações de horário de funcionamento do model.
        """
        user = request.user
        if user.barbershop_id is None:
            raise PermissionDenied('Usuário sem barbearia vinculada.')

        barbeiro_id = request.query_params.get('barbeiro')
        servico_id = request.query_params.get('servico')
        data_param = request.query_params.get('data')
        exclude_appointment_id = request.query_params.get('exclude_appointment_id')
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
            barbeiro = Barber.objects.select_related('barbershop').get(
                id=barbeiro_id, barbershop_id=user.barbershop_id, ativo=True
            )
        except (Barber.DoesNotExist, ValueError):
            return Response({'detail': 'Barbeiro não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            servico = Service.objects.get(
                id=servico_id, barbershop_id=user.barbershop_id, ativo=True
            )
        except (Service.DoesNotExist, ValueError):
            return Response({'detail': 'Serviço não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            data = datetime.strptime(data_param, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Data inválida. Use o formato YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validação do exclude_appointment_id (opcional)
        exclude_appointment = None
        if exclude_appointment_id:
            try:
                exclude_appointment = Appointment.objects.select_related(
                    'cliente', 'barbeiro', 'servico', 'barbershop'
                ).get(pk=exclude_appointment_id)
            except (Appointment.DoesNotExist, ValueError):
                return Response({'detail': 'Agendamento a excluir não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            # Verifica se pertence à barbearia do usuário
            if exclude_appointment.barbershop_id != user.barbershop_id:
                return Response({'detail': 'Agendamento a excluir não pertence à sua barbearia.'}, status=status.HTTP_404_NOT_FOUND)

            # Verifica permissão do usuário para reagendar
            if user.is_cliente:
                if exclude_appointment.cliente_id != user.pk:
                    return Response({'detail': 'Sem permissão para reagendar este agendamento.'}, status=status.HTTP_403_FORBIDDEN)
            elif user.is_barbeiro:
                barbeiro_perfil = getattr(user, 'perfil_barbeiro', None)
                if not barbeiro_perfil or exclude_appointment.barbeiro_id != barbeiro_perfil.pk:
                    return Response({'detail': 'Barbeiros só podem gerenciar a própria agenda.'}, status=status.HTTP_403_FORBIDDEN)

            # Verifica se status permite reagendamento
            if exclude_appointment.status not in [Appointment.Status.AGENDADO, Appointment.Status.CONFIRMADO]:
                return Response(
                    {'detail': f'Agendamento com status {exclude_appointment.get_status_display()} não pode ser reagendado.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Se o agendamento a excluir for de outro barbeiro, não tentamos excluí-lo
            # da lista de ocupados (já não estaria lá). Apenas ignoramos a exclusão.
            if exclude_appointment.barbeiro_id != int(barbeiro_id):
                exclude_appointment = None

        duracao = timedelta(minutes=servico.duracao)

        inicio = timezone.make_aware(datetime.combine(data, barbeiro.barbershop.horario_abertura))
        limite = timezone.make_aware(datetime.combine(data, barbeiro.barbershop.horario_fechamento)) - duracao

        agendamentos = Appointment.objects.filter(
            barbeiro=barbeiro,
            data_hora__date=data,
        ).exclude(status=Appointment.Status.CANCELADO).select_related('servico')

        # Exclui o agendamento original da consulta de horários ocupados durante reagendamento
        if exclude_appointment:
            agendamentos = agendamentos.exclude(pk=exclude_appointment.pk)

        ocupados = [
            (
                timezone.localtime(agendamento.data_hora),
                timezone.localtime(agendamento.data_hora)
                + timedelta(minutes=agendamento.servico.duracao),
            )
            for agendamento in agendamentos
        ]

        slots = []
        slot_atual = inicio
        agora_local = timezone.localtime()
        while slot_atual <= limite:
            fim_slot = slot_atual + duracao
            conflita = any(inicio_ocupado < fim_slot and slot_atual < fim_ocupado
                           for inicio_ocupado, fim_ocupado in ocupados)
            if not conflita and not (data == agora_local.date() and slot_atual <= agora_local):
                slots.append(slot_atual.strftime('%H:%M'))
            slot_atual += duracao

        return Response({'data': data.isoformat(), 'slots': slots})

    @action(detail=False, methods=['get'], url_path='revenue-report')
    def revenue_report(self, request):
        """
        GET /api/v1/appointments/revenue-report/?start=2026-01-01&end=2026-12-31

        Relatório de faturamento baseado no preço histórico dos agendamentos
        concluídos (status = realizado). Usa `preco_historico` para garantir
        que alterações posteriores no preço dos serviços não afetem o
        faturamento já consolidado.

        Parâmetros:
        - start: data inicial (YYYY-MM-DD) - opcional, padrão 30 dias atrás
        - end: data final (YYYY-MM-DD) - opcional, padrão hoje
        - barbeiro: ID do barbeiro para filtrar - opcional

        Retorna:
        - total_revenue: soma dos preços históricos
        - total_appointments: contagem de agendamentos realizados
        - by_barber: faturamento agrupado por barbeiro
        - by_service: faturamento agrupado por serviço
        - daily: faturamento diário
        """
        user = request.user
        if user.barbershop_id is None:
            raise PermissionDenied('Usuário sem barbearia vinculada.')

        # Parâmetros de data
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')
        barbeiro_param = request.query_params.get('barbeiro')

        hoje = timezone.localdate()
        try:
            start_date = datetime.strptime(start_param, '%Y-%m-%d').date() if start_param else hoje - timedelta(days=30)
        except ValueError:
            return Response({'detail': 'Data inicial inválida. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            end_date = datetime.strptime(end_param, '%Y-%m-%d').date() if end_param else hoje
        except ValueError:
            return Response({'detail': 'Data final inválida. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'detail': 'Data inicial não pode ser maior que final.'}, status=status.HTTP_400_BAD_REQUEST)

        # Base queryset: apenas agendamentos realizados da barbearia do usuário
        qs = Appointment.objects.filter(
            barbershop_id=user.barbershop_id,
            status=Appointment.Status.REALIZADO,
            data_hora__date__gte=start_date,
            data_hora__date__lte=end_date,
        ).select_related('barbeiro__user', 'servico')

        # Filtro opcional por barbeiro
        if barbeiro_param:
            try:
                qs = qs.filter(barbeiro_id=int(barbeiro_param))
            except ValueError:
                return Response({'detail': 'ID do barbeiro inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Total geral usando preco_historico
        total = qs.aggregate(
            total_revenue=Sum('preco_historico'),
            total_appointments=Count('id')
        )

        # Por barbeiro
        by_barber = list(qs.values('barbeiro__user__nome').annotate(
            revenue=Sum('preco_historico'),
            count=Count('id')
        ).order_by('-revenue'))

        # Por serviço
        by_service = list(qs.values('servico__nome').annotate(
            revenue=Sum('preco_historico'),
            count=Count('id')
        ).order_by('-revenue'))

        # Diário
        daily = list(qs.extra(
            select={'date': 'DATE(data_hora)'}
        ).values('date').annotate(
            revenue=Sum('preco_historico'),
            count=Count('id')
        ).order_by('date'))

        # Converter Decimal para string para serialização JSON
        def format_decimal(val):
            if val is None:
                return '0.00'
            return str(val)

        return Response({
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'total_revenue': format_decimal(total['total_revenue']),
            'total_appointments': total['total_appointments'] or 0,
            'by_barber': [
                {'barbeiro': item['barbeiro__user__nome'], 'revenue': format_decimal(item['revenue']), 'count': item['count']}
                for item in by_barber
            ],
            'by_service': [
                {'servico': item['servico__nome'], 'revenue': format_decimal(item['revenue']), 'count': item['count']}
                for item in by_service
            ],
            'daily': [
                {'date': item['date'], 'revenue': format_decimal(item['revenue']), 'count': item['count']}
                for item in daily
            ],
        })


class IsAdminOrBarberRole(permissions.BasePermission):
    """Permite alterar uma agenda apenas ao admin ou ao barbeiro responsável."""

    def has_permission(self, request, view):
        return IsAdminRole().has_permission(request, view) or IsBarberRole().has_permission(
            request, view
        )
