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
        read_only_fields = ['id', 'created_at']


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
