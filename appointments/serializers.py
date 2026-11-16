"""
Serializers do app appointments.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from config.tenancy import TenantScopedPrimaryKeyRelatedField

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    # TEN-01: `cliente`, `barbeiro` e `servico` só aceitam e só listam registros
    # da barbearia do usuário autenticado. Um ID de outra barbearia recebe a
    # mesma resposta de um ID inexistente, e o registro alheio não é lido.
    serializer_related_field = TenantScopedPrimaryKeyRelatedField

    # Campos "achatados", só leitura, para o frontend não precisar de
    # chamadas extras para montar a tela de agendamento.
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    barbeiro_nome = serializers.CharField(source='barbeiro.user.nome', read_only=True)
    servico_nome = serializers.CharField(source='servico.nome', read_only=True)
    servico_preco = serializers.CharField(source='servico.preco', read_only=True)
    servico_duracao = serializers.IntegerField(source='servico.duracao', read_only=True)
    # Preço histórico praticado no momento do agendamento (somente leitura).
    # Não pode ser manipulado pelo cliente — é definido automaticamente no backend.
    preco_historico = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = [
            'id', 'barbershop', 'cliente', 'cliente_nome', 'barbeiro',
            'barbeiro_nome', 'servico', 'servico_nome', 'servico_preco',
            'servico_duracao', 'data_hora', 'status', 'observacoes',
            'preco_historico', 'created_at',
        ]
        read_only_fields = ['id', 'barbershop', 'preco_historico', 'created_at']

    def validate(self, attrs):
        # Validar status ANTES de verificar permissões: não permitir
        # PATCH (reagendamento ou alteração) em agendamentos cancelados ou realizados.
        if self.instance:
            if self.instance.status == Appointment.Status.CANCELADO:
                raise serializers.ValidationError(
                    {'status': 'Não é possível alterar um agendamento cancelado.'}
                )
            if self.instance.status == Appointment.Status.REALIZADO:
                raise serializers.ValidationError(
                    {'status': 'Não é possível alterar um agendamento realizado.'}
                )

        # Reaproveita, na camada de API, a mesma regra de consistência
        # do Appointment.clean(): barbeiro e serviço precisam pertencer
        # à barbearia do usuário autenticado.
        appointment = Appointment()
        if self.instance:
            # Não altere a instância persistida durante a validação de PATCH.
            # A cópia também preserva o pk para a checagem de conflitos
            # ignorar o próprio agendamento.
            for field in Appointment._meta.fields:
                setattr(appointment, field.attname, getattr(self.instance, field.attname))
            # Sem esta linha, esta cópia continua com `_state.adding=True`
            # mesmo já tendo um pk copiado. O `validate_unique()` chamado
            # dentro de `full_clean()` logo abaixo usa exatamente esse
            # estado para decidir se exclui o próprio registro da
            # checagem de unicidade — como não excluía, QUALQUER update
            # válido era recusado com "Agendamento com este ID já existe"
            # (bug original, o pk colidia com o próprio registro).
            appointment._state.adding = False
        for field, value in attrs.items():
            setattr(appointment, field, value)

        barbeiro = appointment.barbeiro if appointment.barbeiro_id else None
        servico = appointment.servico if appointment.servico_id else None
        cliente = appointment.cliente if appointment.cliente_id else None
        request = self.context.get('request')
        barbershop_id = appointment.barbershop_id
        if not barbershop_id and request:
            barbershop_id = request.user.barbershop_id
            appointment.barbershop_id = barbershop_id
        # TEN-02: sem barbearia, recusa antes de qualquer regra de negócio.
        # Antes, as checagens abaixo eram puladas quando barbershop_id era
        # vazio, e o full_clean() consultava a agenda do barbeiro de outra
        # barbearia. A view já recusa antes (HasBarbershop); esta segunda
        # camada não depende dela nem do escopo dos campos relacionais.
        if not barbershop_id:
            raise PermissionDenied('Usuário sem barbearia vinculada.')

        if barbeiro and barbeiro.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'barbeiro': 'Este barbeiro não pertence à sua barbearia.'}
            )
        if barbeiro and not barbeiro.ativo:
            raise serializers.ValidationError(
                {'barbeiro': 'Este barbeiro está inativo.'}
            )
        if servico and servico.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'servico': 'Este serviço não pertence à sua barbearia.'}
            )
        if cliente and cliente.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'cliente': 'Este cliente não pertence à sua barbearia.'}
            )

        # BUS-15: o status inicial é definido pelo backend. O cliente só cria
        # horários "agendado", que aguardam a confirmação da barbearia; mandar
        # outro status na requisição não contorna essa aprovação.
        if (
            self.instance is None
            and request
            and request.user.is_cliente
            and attrs.get('status', Appointment.Status.AGENDADO) != Appointment.Status.AGENDADO
        ):
            raise PermissionDenied(
                'O status inicial é definido pela barbearia: o agendamento começa como '
                'agendado e aguarda confirmação.'
            )

        if (
            self.instance
            and request
            and request.user.is_cliente
            and 'cliente' in attrs
            and attrs['cliente'].pk != self.instance.cliente_id
        ):
            raise PermissionDenied('Clientes não podem transferir o próprio agendamento.')

        # Clientes podem alterar o status para 'cancelado' ou reagendar (próprio agendamento)
        if (
            self.instance
            and request
            and request.user.is_cliente
            and 'status' in attrs
            and attrs['status'] != self.instance.status
        ):
            if attrs['status'] != Appointment.Status.CANCELADO:
                raise PermissionDenied('Clientes só podem cancelar o próprio agendamento.')

        if request and request.user.is_barbeiro and 'barbeiro' in attrs:
            # Verifica se o usuário tem perfil de barbeiro antes de acessá-lo
            if not hasattr(request.user, 'perfil_barbeiro') or request.user.perfil_barbeiro is None:
                raise PermissionDenied('Usuário não possui perfil de barbeiro associado.')
            if attrs['barbeiro'].pk != request.user.perfil_barbeiro.pk:
                raise serializers.ValidationError(
                    {'barbeiro': 'Barbeiros só podem gerenciar a própria agenda.'}
                )

        # Validação específica para clientes em PATCH (reagendamento ou cancelamento)
        if (
            self.instance
            and request
            and request.user.is_cliente
        ):
            if attrs.get('status') == Appointment.Status.CANCELADO:
                # Cancelamento é uma operação de estado, não um
                # reagendamento. Não deixe que dados de agenda sejam
                # alterados no mesmo PATCH.
                campos_extras = set(attrs) - {'status'}
                if campos_extras:
                    raise serializers.ValidationError({
                        'status': (
                            'Ao cancelar, envie somente o campo status com o valor cancelado. '
                            'Horário, barbeiro e serviço são preservados.'
                        )
                    })
            else:
                # Reagendamento pode alterar data, barbeiro, serviço e
                # observações, mas não pode alterar o cliente nem outros
                # campos administrativos.
                campos_permitidos_cliente = {'data_hora', 'barbeiro', 'servico', 'observacoes', 'status'}
                campos_nao_permitidos = set(attrs.keys()) - campos_permitidos_cliente
                if campos_nao_permitidos:
                    raise PermissionDenied(
                        f'Clientes não podem alterar os campos: {", ".join(campos_nao_permitidos)}. '
                        f'Campos permitidos para reagendamento: {", ".join(campos_permitidos_cliente)}.'
                    )

                # Se está tentando alterar data_hora, barbeiro ou servico, validar se agendamento permite
                if self.instance.status not in [Appointment.Status.AGENDADO, Appointment.Status.CONFIRMADO]:
                    if any(campo in attrs for campo in ['data_hora', 'barbeiro', 'servico']):
                        raise PermissionDenied(
                            'Não é possível reagendar agendamentos com status '
                            f'{self.instance.get_status_display()}. Apenas agendados ou confirmados podem ser reagendados.'
                        )

                # Validação de data_hora não ser no passado para reagendamento
                if 'data_hora' in attrs and attrs['data_hora'] < timezone.now():
                    raise serializers.ValidationError(
                        {'data_hora': 'Não é possível reagendar para uma data/hora que já passou.'}
                    )

                # BUS-03: a barbearia confirmou o horário antigo, não o novo.
                # Quando o cliente muda horário, barbeiro ou serviço de um
                # horário confirmado, ele volta a "agendado" e precisa de nova
                # confirmação. Alterações do admin e do barbeiro (o lado da
                # barbearia) mantêm o status.
                if (
                    self.instance.status == Appointment.Status.CONFIRMADO
                    and self._altera_agenda(self.instance, attrs)
                ):
                    attrs['status'] = Appointment.Status.AGENDADO
                    appointment.status = Appointment.Status.AGENDADO

        try:
            appointment.full_clean()
        except DjangoValidationError as error:
            detail = getattr(error, 'message_dict', None) or {'non_field_errors': error.messages}
            raise serializers.ValidationError(detail) from error
        return attrs

    @staticmethod
    def _altera_agenda(instance, attrs):
        """Verdadeiro se o PATCH muda de fato o horário, o barbeiro ou o serviço."""
        if 'data_hora' in attrs and attrs['data_hora'].timestamp() != instance.data_hora.timestamp():
            return True
        if 'barbeiro' in attrs and attrs['barbeiro'].pk != instance.barbeiro_id:
            return True
        if 'servico' in attrs and attrs['servico'].pk != instance.servico_id:
            return True
        return False

    @staticmethod
    def _raise_django_validation_error(error):
        detail = getattr(error, 'message_dict', None) or {
            'non_field_errors': error.messages,
        }
        raise serializers.ValidationError(detail) from error

    @staticmethod
    def _copy_instance(instance):
        """Cria uma cópia persistida para revalidar um PATCH sem mutá-lo."""
        appointment = Appointment()
        for field in Appointment._meta.fields:
            setattr(appointment, field.attname, getattr(instance, field.attname))
        appointment._state.adding = False
        return appointment

    @staticmethod
    def _lock_barbers(*barber_ids):
        """Trava e recarrega os barbeiros envolvidos na alteração."""
        from barbershops.models import Barber

        ids = sorted({barber_id for barber_id in barber_ids if barber_id})
        barbers = Barber.objects.select_for_update().filter(pk__in=ids).order_by('pk')
        return {barber.pk: barber for barber in barbers}

    def create(self, validated_data):
        """
        Revalida depois de bloquear a agenda do barbeiro. A validação normal
        do DRF acontece antes do save; sem esta segunda validação, duas
        requisições simultâneas poderiam ambas não enxergar o outro horário.
        """
        with transaction.atomic():
            barber_id = validated_data['barbeiro'].pk
            locked_barbers = self._lock_barbers(barber_id)
            # Usa o registro lido após a trava; assim uma desativação
            # concorrente também é observada antes da gravação.
            validated_data['barbeiro'] = locked_barbers[barber_id]
            # Definir preço histórico do serviço no momento da criação
            # Nunca confiar em preço enviado pelo frontend
            servico = validated_data['servico']
            validated_data['preco_historico'] = servico.preco
            appointment = Appointment(**validated_data)
            try:
                appointment.full_clean()
            except DjangoValidationError as error:
                self._raise_django_validation_error(error)
            appointment.save()
            return appointment

    def update(self, instance, validated_data):
        """Aplica o mesmo bloqueio e revalidação para remarcações/PATCH."""
        with transaction.atomic():
            new_barber = validated_data.get('barbeiro', instance.barbeiro)
            locked_barbers = self._lock_barbers(instance.barbeiro_id, new_barber.pk)
            validated_data['barbeiro'] = locked_barbers[new_barber.pk]

            # Lógica do preço histórico:
            # - Se o serviço for alterado, atualizar para o preço vigente do novo serviço
            # - Se apenas horário/barbeiro/observações mudarem, preservar o preço histórico original
            if 'servico' in validated_data and validated_data['servico'] != instance.servico:
                validated_data['preco_historico'] = validated_data['servico'].preco
            elif 'preco_historico' in validated_data:
                # Impedir manipulação do preço histórico pelo frontend
                validated_data.pop('preco_historico')

            candidate = self._copy_instance(instance)
            for field, value in validated_data.items():
                setattr(candidate, field, value)
            try:
                candidate.full_clean()
            except DjangoValidationError as error:
                self._raise_django_validation_error(error)

            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            return instance
