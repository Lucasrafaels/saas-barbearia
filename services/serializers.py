"""
Serializers do app services.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    # Sobrescreve duracao para rejeitar valores <= 0
    duracao = serializers.IntegerField(
        min_value=1,
        help_text="Duração em minutos (mínimo 1)"
    )
    # Sobrescreve preco para rejeitar valores negativos (zero é permitido)
    preco = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal('0.00'),
        help_text="Preço do serviço (mínimo 0.00)"
    )

    class Meta:
        model = Service
        fields = [
            'id', 'barbershop', 'nome', 'descricao', 'preco',
            'duracao', 'ativo', 'created_at',
        ]
        # `barbershop` é preenchido automaticamente pelo
        # TenantScopedQuerysetMixin, não pelo cliente da API.
        read_only_fields = ['id', 'barbershop', 'created_at']
