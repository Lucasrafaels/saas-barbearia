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

    def validate(self, attrs):
        # Criar uma barbearia é o fluxo de onboarding (ver
        # BarbershopViewSet.perform_create): só faz sentido para quem
        # ainda não pertence a nenhuma. Sem esta checagem, um usuário que
        # já tem tenant também conseguia criar — a barbearia era
        # persistida mesmo assim, só o vínculo de admin é que não
        # acontecia, deixando um registro órfão no banco (bug original).
        request = self.context.get('request')
        if self.instance is None and request and request.user.barbershop_id:
            raise serializers.ValidationError(
                'Você já pertence a uma barbearia e não pode criar outra.'
            )
        return attrs


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

    def get_fields(self):
        """A associação profissional não pode ser transferida por PATCH."""
        fields = super().get_fields()
        if self.instance is not None:
            fields['user'].read_only = True
        return fields

    def validate(self, attrs):
        """Executa no fluxo REST a mesma consistência definida no model."""
        request = self.context.get('request')
        barber = self.instance or Barber()
        barber.user = attrs.get('user', getattr(barber, 'user', None))

        if not barber.barbershop_id and request:
            barber.barbershop_id = request.user.barbershop_id

        # Block ADMIN users from being converted to barbers.
        user = attrs.get('user', getattr(barber, 'user', None))
        if user and getattr(user, 'tipo_perfil', None) == 'admin':
            raise serializers.ValidationError(
                {'user': 'Usuários administradores não podem ser convertidos em barbeiros.'}
            )

        # A promoção efetiva é feita pela view, dentro da mesma transação que
        # salva o perfil. Para validar a combinação antes de gravar, usamos
        # uma cópia em memória do papel esperado, sem alterar o User real.
        is_creation_with_promotion = (
            self.instance is None
            and attrs.get('ativo', True) is True
            and user is not None
            and getattr(user, 'tipo_perfil', None) == 'cliente'
        )
        is_reactivation = (
            self.instance is not None
            and attrs.get('ativo', getattr(self.instance, 'ativo', False)) is True
            and getattr(self.instance, 'ativo', False) is False
        )

        original_profile = getattr(user, 'tipo_perfil', None)
        try:
            if is_creation_with_promotion or is_reactivation:
                user.tipo_perfil = 'barbeiro'
            barber.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        finally:
            if user is not None:
                user.tipo_perfil = original_profile
        return attrs
