"""
Views do app accounts: login JWT customizado, logout (blacklist) e
o ViewSet de gestão de usuários.
"""
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config.permissions import IsAdminRole, IsSelfOrAdmin
from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    PublicRegistrationSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — retorna os tokens access e refresh."""
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/ — invalida (blacklist) o refresh token
    enviado no corpo da requisição: {"refresh": "<token>"}.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'O campo "refresh" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token inválido ou já expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class RegistrationView(APIView):
    """POST /api/v1/auth/register/ — cria uma conta inicial de cliente."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PublicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserViewSet(viewsets.ModelViewSet):
    """
    Gestão de usuários da barbearia. Listar/remover é restrito a
    administradores; qualquer usuário autenticado pode consultar os
    próprios dados em /users/me/.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'create', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminRole()]
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsSelfOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_superuser:
            return queryset
        return queryset.filter(barbershop_id=user.barbershop_id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/v1/users/me/ — dados do usuário autenticado."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
