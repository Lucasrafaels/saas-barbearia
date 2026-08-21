"""
Serializers do app barbershops.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Barber, Barbershop


class BarbershopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbershop
        fields = [
            'id', 'nome', 'endereco', 'telefone', 'email',
            'horario_abertura', 'horario_fechamento', 'logo', 'ativo',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class BarberSerializer(serializers.ModelSerializer):
    # Campos "achatados" do usuário vinculado, só para leitura — evita o
    # frontend precisar fazer uma segunda chamada para exibir nome/e-mail.
    nome = serializers.CharField(source='user.nome', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Barber
        fields = [
            'id', 'user', 'nome', 'email', 'barbershop',
            'especialidade', 'ativo', 'created_at',
        ]
        # `barbershop` é preenchido automaticamente pelo
        # TenantScopedQuerysetMixin, não pelo cliente da API.
        read_only_fields = ['id', 'barbershop', 'created_at']

    def validate(self, attrs):
        """Executa no fluxo REST a mesma consistência definida no model."""
        request = self.context.get('request')
        barber = self.instance or Barber()
        barber.user = attrs.get('user', getattr(barber, 'user', None))

        if not barber.barbershop_id and request:
            barber.barbershop_id = request.user.barbershop_id

        try:
            barber.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return attrs
