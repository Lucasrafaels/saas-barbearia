"""
Modelo de agendamentos: liga um cliente, um barbeiro e um serviço em
uma data/hora específica, com um status de acompanhamento.
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

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
        on_delete=models.PROTECT,
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='cliente',
        related_name='agendamentos_cliente',
        on_delete=models.PROTECT,
        # Restringe apenas as opções mostradas em formulários (ex.: admin);
        # não é uma constraint de banco de dados.
        limit_choices_to={'tipo_perfil': 'cliente'},
    )
    barbeiro = models.ForeignKey(
        'barbershops.Barber',
        verbose_name='barbeiro',
        related_name='agendamentos',
        on_delete=models.PROTECT,
    )
    servico = models.ForeignKey(
        'services.Service',
        verbose_name='serviço',
        related_name='agendamentos',
        on_delete=models.PROTECT,
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
        indexes = [
            models.Index(fields=['barbeiro', 'data_hora']),
            models.Index(fields=['barbershop', 'data_hora']),
        ]

    def __str__(self):
        return f'{self.cliente.nome} com {self.barbeiro.user.nome} em {self.data_hora:%d/%m/%Y %H:%M}'

    def clean(self):
        # Garante consistência multi-tenant: barbeiro e serviço escolhidos
        # precisam pertencer à mesma barbearia do agendamento. Isso evita,
        # por exemplo, agendar um serviço da Barbearia A com um barbeiro
        # da Barbearia B.
        errors = {}
        if self.cliente_id:
            # Import local evita um ciclo de importação no carregamento dos
            # modelos; o campo precisa apontar para um usuário cliente.
            from accounts.models import User

            if self.cliente.tipo_perfil != User.TipoPerfil.CLIENTE:
                errors['cliente'] = 'O usuário selecionado deve ter perfil de cliente.'
            elif (
                self.barbershop_id
                and self.cliente.barbershop_id != self.barbershop_id
            ):
                errors['cliente'] = 'Este cliente não pertence a esta barbearia.'
        validating_new_booking = not self.pk
        if self.pk:
            persisted = type(self).objects.filter(pk=self.pk).values(
                'barbeiro_id', 'servico_id', 'data_hora'
            ).first()
            validating_new_booking = bool(persisted and any(
                persisted[field] != getattr(self, field)
                for field in ('barbeiro_id', 'servico_id', 'data_hora')
            ))
        if self.barbeiro_id and self.barbershop_id and self.barbeiro.barbershop_id != self.barbershop_id:
            errors['barbeiro'] = 'Este barbeiro não pertence a esta barbearia.'
        elif validating_new_booking and self.barbeiro_id and not self.barbeiro.ativo:
            errors['barbeiro'] = 'Este barbeiro está inativo e não pode receber agendamentos.'
        if self.servico_id and self.barbershop_id and self.servico.barbershop_id != self.barbershop_id:
            errors['servico'] = 'Este serviço não pertence a esta barbearia.'
        elif validating_new_booking and self.servico_id and not self.servico.ativo:
            errors['servico'] = 'Este serviço está inativo e não pode ser agendado.'
        if errors:
            raise ValidationError(errors)

        self._validar_horario_funcionamento()
        self._validar_nao_permite_agendamento_no_passado()
        self._validar_conflito_horario()

    def _validar_horario_funcionamento(self):
        """
        Garante que o agendamento — do início ao fim, considerando a
        duração do serviço — acontece dentro do horário de funcionamento
        da barbearia.

        A comparação é feita no fuso horário local (TIME_ZONE do
        projeto), já que `horario_abertura`/`horario_fechamento` são
        horários "de parede" da barbearia, não horários em UTC.
        """
        if not self.barbershop_id or not self.servico_id or not self.data_hora:
            return

        inicio = timezone.localtime(self.data_hora)
        fim = inicio + timedelta(minutes=self.servico.duracao)
        barbershop = self.barbershop

        if inicio.time() < barbershop.horario_abertura:
            raise ValidationError({
                'data_hora': (
                    'O agendamento não pode começar antes do horário de '
                    f'abertura da barbearia ({barbershop.horario_abertura:%H:%M}).'
                )
            })
        # `fim` em um dia diferente do início também é considerado fora do
        # horário de funcionamento — a barbearia não opera de madrugada,
        # atravessando a virada do dia.
        if fim.date() != inicio.date() or fim.time() > barbershop.horario_fechamento:
            raise ValidationError({
                'data_hora': (
                    'O agendamento não pode terminar depois do horário de '
                    f'fechamento da barbearia ({barbershop.horario_fechamento:%H:%M}).'
                )
            })

    def _validar_nao_permite_agendamento_no_passado(self):
        """
        Impede marcar (ou remarcar) um agendamento para uma data/hora que
        já passou.

        Só reavalia a regra quando `data_hora` está sendo definida pela
        primeira vez (criação) ou alterada (remarcação): editar outros
        campos — por exemplo, mudar o status para "realizado" ou incluir
        uma observação — em um agendamento cuja data já passou continua
        permitido. Sem essa distinção, seria impossível encerrar o fluxo
        normal de um agendamento depois do horário marcado.
        """
        if not self.data_hora:
            return

        if self.pk:
            data_hora_persistida = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list('data_hora', flat=True)
                .first()
            )
            if data_hora_persistida == self.data_hora:
                return

        if self.data_hora < timezone.now():
            raise ValidationError(
                {'data_hora': 'Não é possível agendar em uma data/hora que já passou.'}
            )

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
            .filter(
                barbeiro_id=self.barbeiro_id,
                data_hora__lt=fim_novo_agendamento,
                data_hora__gte=self.data_hora - timedelta(minutes=24 * 60),
            )
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
