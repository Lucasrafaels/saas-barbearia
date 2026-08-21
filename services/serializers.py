"""
Serializers do app services.
"""
from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'barbershop', 'nome', 'descricao', 'preco',
            'duracao', 'ativo', 'created_at',
        ]
        # `barbershop` é preenchido automaticamente pelo
        # TenantScopedQuerysetMixin, não pelo cliente da API.
        read_only_fields = ['id', 'barbershop', 'created_at']
