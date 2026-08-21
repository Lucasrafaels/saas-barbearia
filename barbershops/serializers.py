"""
Serializers do app barbershops.
"""
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
