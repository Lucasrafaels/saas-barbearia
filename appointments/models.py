"""
Modelo de agendamentos: liga um cliente, um barbeiro e um serviço em
uma data/hora específica, com um status de acompanhamento.
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from config.models import TimeStampedModel


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        AGENDADO = 'agendado', 'Agendado'
        CONFIRMADO = 'confirmado', 'Confirmado'
        REALIZADO = 'realizado', 'Realizado'
        CANCELADO = 'cancelado', 'Cancelado'

    # Tecnicamente redundante em relação a barbeiro/servico (ambos já
    # levam a uma barbearia), mas mantido explícito de propósito: permite
    # filtrar agendamentos por barbershop_id diretamente, sem precisar de
    # joins — essencial para a arquitetura multi-tenant funcionar de forma
    # simples e eficiente em todos os ViewSets.
    barbershop = models.ForeignKey(
        'barbershops.Barbershop',
        verbose_name='barbearia',
        related_name='agendamentos',
        on_delete=models.CASCADE,
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='cliente',
        related_name='agendamentos_cliente',
        on_delete=models.CASCADE,
        # Restringe apenas as opções mostradas em formulários (ex.: admin);
        # não é uma constraint de banco de dados.
        limit_choices_to={'tipo_perfil': 'cliente'},
    )
    barbeiro = models.ForeignKey(
        'barbershops.Barber',
        verbose_name='barbeiro',
        related_name='agendamentos',
        on_delete=models.CASCADE,
    )
    servico = models.ForeignKey(
        'services.Service',
        verbose_name='serviço',
        related_name='agendamentos',
        on_delete=models.CASCADE,
    )
    data_hora = models.DateTimeField('data e hora')
    status = models.CharField(
        'status',
        max_length=12,
        choices=Status.choices,
        default=Status.AGENDADO,
    )
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        verbose_name = 'agendamento'
        verbose_name_plural = 'agendamentos'
        ordering = ['-data_hora']

    def __str__(self):
        return f'{self.cliente.nome} com {self.barbeiro.user.nome} em {self.data_hora:%d/%m/%Y %H:%M}'

    def clean(self):
        # Garante consistência multi-tenant: barbeiro e serviço escolhidos
        # precisam pertencer à mesma barbearia do agendamento. Isso evita,
        # por exemplo, agendar um serviço da Barbearia A com um barbeiro
        # da Barbearia B.
        errors = {}
        if self.barbeiro_id and self.barbershop_id and self.barbeiro.barbershop_id != self.barbershop_id:
            errors['barbeiro'] = 'Este barbeiro não pertence a esta barbearia.'
        if self.servico_id and self.barbershop_id and self.servico.barbershop_id != self.barbershop_id:
            errors['servico'] = 'Este serviço não pertence a esta barbearia.'
        if errors:
            raise ValidationError(errors)
        self._validar_conflito_horario()

    def _validar_conflito_horario(self):
        """Impede que um barbeiro tenha dois horários ativos sobrepostos."""
        if (
            not self.barbeiro_id
            or not self.servico_id
            or not self.data_hora
            or self.status == self.Status.CANCELADO
        ):
            return

        fim_novo_agendamento = self.data_hora + timedelta(minutes=self.servico.duracao)
        agendamentos = (
            type(self).objects.select_related('servico')
            .filter(barbeiro_id=self.barbeiro_id, data_hora__lt=fim_novo_agendamento)
            .exclude(status=self.Status.CANCELADO)
            .exclude(pk=self.pk)
        )
        for agendamento in agendamentos:
            fim_agendamento_existente = agendamento.data_hora + timedelta(
                minutes=agendamento.servico.duracao
            )
            if fim_agendamento_existente > self.data_hora:
                raise ValidationError(
                    {'data_hora': 'Este barbeiro já possui um agendamento neste horário.'}
                )
