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

BARBEARIA_DESATIVADA_MENSAGEM = (
    'Esta barbearia está desativada: não é possível criar, remarcar, confirmar '
    'ou concluir agendamentos. Consultas e cancelamentos continuam disponíveis.'
)


def barbearia_esta_ativa(barbershop_id):
    """Lê o status atual no banco, sem depender de uma instância em cache."""
    from barbershops.models import Barbershop

    return Barbershop.objects.filter(pk=barbershop_id, ativo=True).exists()


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
    # Preço praticado no momento do agendamento (preservado para histórico
    # financeiro). Se o preço do serviço mudar depois, o agendamento mantém
    # o valor original. Em reagendamentos: troca de horário/barbeiro preserva
    # o preço; troca de serviço atualiza para o preço vigente do novo serviço.
    preco_historico = models.DecimalField(
        'preço histórico',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Preço do serviço no momento da criação/alteração do agendamento',
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

        self._validar_barbearia_ativa()
        self._validar_horario_funcionamento()
        self._validar_nao_permite_agendamento_no_passado()
        self._validar_conflito_horario()
        self._validar_transicao_status()
        self._validar_conclusao_apos_termino()
        self._validar_status_inicial()

    def _validar_status_inicial(self):
        """
        Um agendamento novo nasce "agendado" (aguardando a barbearia) ou,
        quando registrado pela própria barbearia, já "confirmado". Ninguém
        cria um registro novo como cancelado ou realizado. O status
        "realizado" já é recusado antes por `_validar_conclusao_apos_termino`,
        com uma mensagem mais específica.

        Quem pode escolher "confirmado" é decidido na API
        (`AppointmentSerializer.validate`): o cliente não pode.
        """
        if self.pk:
            return
        if self.status not in (self.Status.AGENDADO, self.Status.CONFIRMADO):
            raise ValidationError({
                'status': 'Um agendamento novo começa como agendado (ou confirmado, '
                          'quando registrado pela própria barbearia).'
            })

    def _validar_barbearia_ativa(self):
        """
        Barbearia desativada não opera: não aceita agendamento novo,
        remarcação (horário, barbeiro ou serviço), confirmação nem conclusão.

        Continuam permitidos o cancelamento, que encerra um compromisso que
        não vai acontecer, e a edição de observações. Nenhum registro é
        alterado pela desativação em si, e o histórico segue consultável.
        """
        if not self.barbershop_id or barbearia_esta_ativa(self.barbershop_id):
            return

        persistido = None
        if self.pk:
            persistido = (
                type(self).objects
                .filter(pk=self.pk)
                .values('status', 'barbeiro_id', 'servico_id', 'data_hora')
                .first()
            )
        if persistido is not None:
            remarcando = (
                persistido['barbeiro_id'] != self.barbeiro_id
                or persistido['servico_id'] != self.servico_id
                or persistido['data_hora'] != self.data_hora
            )
            avancando_status = self.status not in (persistido['status'], self.Status.CANCELADO)
            if not remarcando and not avancando_status:
                return

        raise ValidationError({'barbershop': BARBEARIA_DESATIVADA_MENSAGEM})

    def _validar_conclusao_apos_termino(self):
        """
        "Realizado" registra um atendimento que aconteceu e entra no
        faturamento. Só é aceito a partir do término previsto do horário,
        `data_hora + servico.duracao`: o mesmo intervalo que a agenda usa
        para conflitos e horários livres.

        A comparação é entre instantes absolutos (datetimes aware), então o
        TIME_ZONE do projeto só afeta o horário exibido na mensagem. Vale
        para a transição confirmado → realizado e também para um registro
        criado diretamente com status realizado.
        """
        if self.status != self.Status.REALIZADO or not self.data_hora or not self.servico_id:
            return

        if self.pk:
            persistido = (
                type(self).objects
                .filter(pk=self.pk)
                .values('status', 'data_hora', 'servico_id')
                .first()
            )
            if (
                persistido is not None
                and persistido['status'] == self.Status.REALIZADO
                and persistido['data_hora'] == self.data_hora
                and persistido['servico_id'] == self.servico_id
            ):
                return

        termino = self.data_hora + timedelta(minutes=self.servico.duracao)
        if timezone.now() < termino:
            raise ValidationError({
                'status': (
                    'O atendimento só pode ser marcado como realizado após o término '
                    f'previsto, em {timezone.localtime(termino):%d/%m/%Y às %H:%M}.'
                )
            })

    def _validar_horario_funcionamento(self):
        """
        Garante que o agendamento — do início ao fim, considerando a
        duração do serviço — acontece dentro do horário de funcionamento
        da barbearia.

        A comparação é feita no fuso horário local (TIME_ZONE do
        projeto), já que `horario_abertura`/`horario_fechamento` são
        horários "de parede" da barbearia, não horários em UTC.

        Só reavalia a regra quando `data_hora` está sendo definida pela
        primeira vez (criação) ou alterada (remarcação), ou quando o serviço
        muda: a troca por um serviço mais longo muda o horário de término
        (BUS-04). Editar outros campos — por exemplo, mudar o status para
        "realizado" ou incluir uma observação — em um agendamento cujo
        horário já foi validado continua permitido.

        O dia da semana precisa estar entre os dias de funcionamento da
        barbearia (BUS-06). Essa parte só é verificada quando `data_hora`
        muda, para que fechar um dia não trave a edição de horários já
        marcados nele.
        """
        if not self.barbershop_id or not self.servico_id or not self.data_hora:
            return

        # Se o agendamento já existe e nem o data_hora nem o serviço mudaram,
        # pular a validação. Isso permite PATCH parcial (ex.: só observacoes
        # ou status) sem revalidar horário comercial.
        data_hora_mudou = True
        servico_mudou = True
        if self.pk:
            persistido = (
                type(self).objects
                .filter(pk=self.pk)
                .values('data_hora', 'servico_id')
                .first()
            )
            if persistido is not None:
                # Comparar timestamps para evitar problemas de representação de timezone
                # (ex.: UTC vs aware local) quando ambos representam o mesmo instante.
                data_hora_mudou = persistido['data_hora'].timestamp() != self.data_hora.timestamp()
                servico_mudou = persistido['servico_id'] != self.servico_id
        if not data_hora_mudou and not servico_mudou:
            return

        inicio = timezone.localtime(self.data_hora)
        fim = inicio + timedelta(minutes=self.servico.duracao)
        barbershop = self.barbershop

        if data_hora_mudou and not barbershop.abre_no_dia(inicio.date()):
            from barbershops.models import DIAS_DA_SEMANA_NO_PLURAL

            raise ValidationError({
                'data_hora': (
                    f'A barbearia não abre {DIAS_DA_SEMANA_NO_PLURAL[inicio.isoweekday()]}. '
                    'Escolha outro dia.'
                )
            })

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
            # Comparar timestamps para evitar problemas de representação de timezone
            # (ex.: UTC vs aware local) quando ambos representam o mesmo instante.
            if data_hora_persistida is not None and data_hora_persistida.timestamp() == self.data_hora.timestamp():
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

    def _validar_transicao_status(self):
        """Valida transições permitidas de status (máquina de estados).

        Política:
        - agendado → confirmado ou cancelado
        - confirmado → realizado ou cancelado
        - realizado → estado final (sem transições)
        - cancelado → estado final (sem transições)
        - confirmado → agendado só numa remarcação (horário, barbeiro ou
          serviço alterados): o novo horário volta a aguardar a aprovação
          da barbearia (BUS-03). Sem remarcação, a reabertura é recusada.

        Não permite agendado → realizado diretamente. O status de um
        registro novo é tratado por `_validar_status_inicial`.
        """
        if not self.pk:
            return

        persistido = (
            type(self).objects
            .filter(pk=self.pk)
            .values('status', 'data_hora', 'barbeiro_id', 'servico_id')
            .first()
        )
        if persistido is None:
            return
        status_atual = persistido['status']

        # Define transições permitidas conforme a política única
        transicoes_permitidas = {
            self.Status.AGENDADO: [self.Status.CONFIRMADO, self.Status.CANCELADO],
            self.Status.CONFIRMADO: [self.Status.REALIZADO, self.Status.CANCELADO],
            self.Status.REALIZADO: [],  # Estado final
            self.Status.CANCELADO: [],  # Estado final
        }

        novo_status = self.status
        if novo_status != status_atual:
            permitidos = list(transicoes_permitidas.get(status_atual, []))
            remarcando = self.data_hora is not None and (
                persistido['data_hora'].timestamp() != self.data_hora.timestamp()
                or persistido['barbeiro_id'] != self.barbeiro_id
                or persistido['servico_id'] != self.servico_id
            )
            if status_atual == self.Status.CONFIRMADO and remarcando:
                permitidos.append(self.Status.AGENDADO)
            if novo_status not in permitidos:
                raise ValidationError({
                    'status': f'Transição inválida: {status_atual} → {novo_status}. '
                              f'Transições permitidas de {status_atual}: {permitidos if permitidos else "nenhuma (estado final)"}'
                })

    def _validar_campos_cliente_nao_autorizados(self):
        """Valida que clientes não alteram campos não autorizados em PATCH."""
        if not self.pk:
            return

        # Import local evita ciclo
        from accounts.models import User

        # Verifica se a validação está vindo de um request de cliente
        # (a instância não tem acesso ao request, mas podemos verificar
        # se há tentativa de alterar campos sensíveis)
        # Esta validação será complementada no serializer com o request context
