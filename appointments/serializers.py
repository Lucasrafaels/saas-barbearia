"""
Serializers do app appointments.
"""
from rest_framework import serializers

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
        barbeiro = attrs.get('barbeiro') or getattr(self.instance, 'barbeiro', None)
        servico = attrs.get('servico') or getattr(self.instance, 'servico', None)
        request = self.context.get('request')
        barbershop_id = request.user.barbershop_id if request else None

        if barbeiro and barbershop_id and barbeiro.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'barbeiro': 'Este barbeiro não pertence à sua barbearia.'}
            )
        if servico and barbershop_id and servico.barbershop_id != barbershop_id:
            raise serializers.ValidationError(
                {'servico': 'Este serviço não pertence à sua barbearia.'}
            )
        return attrs
