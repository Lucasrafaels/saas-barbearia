"""
Serializers do app accounts.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer de leitura/edição de usuários já existentes."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nome', 'tipo_perfil', 'barbershop',
            'is_active', 'created_at',
        ]
        # `barbershop` nunca é editável por este serializer — trocar de
        # tenant não é uma operação de "editar meu cadastro" nem de
        # "admin gerencia usuário", em lugar nenhum do sistema (mesmo
        # padrão de `barbershop` sempre read-only já usado em
        # BarberSerializer/AppointmentSerializer).
        read_only_fields = ['id', 'created_at', 'barbershop']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        requester = getattr(request, 'user', None)
        # `tipo_perfil` só pode ser alterado por um admin (ou superuser).
        # Sem isso, IsSelfOrAdmin libera o próprio usuário para editar seu
        # cadastro, e nada impedia um cliente autenticado de se
        # autopromover via PATCH /users/{seu_id}/ (bug original).
        is_admin = bool(
            requester
            and requester.is_authenticated
            and (requester.is_superuser or requester.tipo_perfil == User.TipoPerfil.ADMIN)
        )
        if not is_admin:
            self.fields['tipo_perfil'].read_only = True

    def validate_tipo_perfil(self, value):
        # Mesma regra já aplicada na criação (UserCreateSerializer): este
        # endpoint genérico nunca é o caminho para conceder papel de
        # administrador, nem para um admin promover alguém a admin.
        if value == User.TipoPerfil.ADMIN:
            raise serializers.ValidationError(
                'Não é possível definir o papel de administrador por este endpoint.'
            )
        return value


class PasswordValidationMixin:
    """Aplica os validadores de senha configurados no Django à API."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        password = attrs.get('password')
        if not password:
            return attrs

        user = User(email=attrs.get('email', ''), nome=attrs.get('nome', ''))
        try:
            validate_password(password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': error.messages}) from error
        return attrs


class UserCreateSerializer(PasswordValidationMixin, serializers.ModelSerializer):
    """Serializer usado para cadastro de novos usuários (recebe senha)."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'password', 'tipo_perfil', 'barbershop']
        read_only_fields = ['id', 'barbershop']

    def validate_tipo_perfil(self, value):
        if value == User.TipoPerfil.ADMIN:
            raise serializers.ValidationError(
                'Administradores não podem ser criados por este endpoint.'
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        request = self.context.get('request')
        if not request or not request.user.barbershop_id:
            raise serializers.ValidationError(
                {'barbershop': 'O administrador precisa pertencer a uma barbearia.'}
            )
        return User.objects.create_user(
            password=password,
            barbershop=request.user.barbershop,
            **validated_data,
        )


class PublicRegistrationSerializer(PasswordValidationMixin, serializers.ModelSerializer):
    """Cadastro público inicial, sempre criado como cliente sem tenant."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customiza o token JWT para embutir dados básicos do usuário
    (nome, tipo_perfil, barbershop_id), evitando uma chamada extra do
    frontend logo após o login.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['nome'] = user.nome
        token['tipo_perfil'] = user.tipo_perfil
        token['barbershop_id'] = user.barbershop_id
        return token