"""
Serializers do app accounts.
"""
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


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer usado para cadastro de novos usuários (recebe senha)."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'password', 'tipo_perfil', 'barbershop']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PublicRegistrationSerializer(serializers.ModelSerializer):
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
