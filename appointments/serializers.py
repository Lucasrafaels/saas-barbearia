"""
Serializers do app appointments.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    # Campos "achatados", só leitura, para o frontend não precisar de
    # chamadas extras para montar a tela de agendamento.
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    barbeiro_nome = serializers.CharField(source='barbeiro.user.nome', read_only=True)
    servico_nome = serializers.CharField(source='servico.nome', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'barbershop', 'cliente', 'cliente_nome', 'barbeiro',
            'barbeiro_nome', 'servico', 'servico_nome', 'data_hora',
            'status', 'observacoes', 'created_at',
        ]
        read_only_fields = ['id', 'barbershop', 'created_at']

    def validate(self, attrs):
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
        request = self.context.get('request')
        barbershop_id = appointment.barbershop_id
        if not barbershop_id and request:
            barbershop_id = request.user.barbershop_id
            appointment.barbershop_id = barbershop_id

        if barbeiro and barbershop_id and barbeiro.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'barbeiro': 'Este barbeiro não pertence à sua barbearia.'}
            )
        if servico and barbershop_id and servico.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'servico': 'Este serviço não pertence à sua barbearia.'}
            )

        if (
            self.instance
            and request
            and request.user.is_cliente
            and 'cliente' in attrs
            and attrs['cliente'].pk != self.instance.cliente_id
        ):
            raise PermissionDenied('Clientes não podem transferir o próprio agendamento.')

        # Clientes só podem alterar o status para 'cancelado' (próprio agendamento)
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

        try:
            appointment.full_clean()
        except DjangoValidationError as error:
            detail = getattr(error, 'message_dict', None) or {'non_field_errors': error.messages}
            raise serializers.ValidationError(detail) from error
        return attrs

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
        """Usa o próprio barbeiro como trava estável da agenda dele."""
        from barbershops.models import Barber

        ids = sorted({barber_id for barber_id in barber_ids if barber_id})
        list(Barber.objects.select_for_update().filter(pk__in=ids).order_by('pk'))

    def create(self, validated_data):
        """
        Revalida depois de bloquear a agenda do barbeiro. A validação normal
        do DRF acontece antes do save; sem esta segunda validação, duas
        requisições simultâneas poderiam ambas não enxergar o outro horário.
        """
        with transaction.atomic():
            self._lock_barbers(validated_data.get('barbeiro').pk)
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
            self._lock_barbers(instance.barbeiro_id, new_barber.pk)

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
