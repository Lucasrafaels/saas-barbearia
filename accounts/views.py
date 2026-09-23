"""
Views do app accounts: login JWT customizado, logout (blacklist) e
o ViewSet de gestão de usuários.
"""
from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from config.permissions import IsAdminRole, IsSelfOrAdmin
from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    ActiveUserTokenRefreshSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PublicRegistrationSerializer,
    UserCreateSerializer,
    UserSerializer,
    revoke_user_refresh_tokens,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — retorna os tokens access e refresh."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'login'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.pop('refresh', None)
        if refresh:
            self._set_refresh_cookie(response, refresh)
        return response

    @staticmethod
    def _set_refresh_cookie(response, refresh):
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            secure=settings.JWT_REFRESH_COOKIE_SECURE,
            samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
            path=settings.JWT_REFRESH_COOKIE_PATH,
        )


class ThrottledTokenRefreshView(TokenRefreshView):
    """Aplica limite específico também a tentativas de refresh."""
    throttle_scope = 'refresh'
    throttle_classes = [ScopedRateThrottle]
    serializer_class = ActiveUserTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh:
            return Response(
                {'detail': 'Cookie de atualização ausente.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = self.get_serializer(data={'refresh': refresh})
        serializer.is_valid(raise_exception=True)
        response = Response({'access': serializer.validated_data['access']})
        rotated_refresh = serializer.validated_data.get('refresh')
        if rotated_refresh:
            CustomTokenObtainPairView._set_refresh_cookie(response, rotated_refresh)
        return response


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/ — invalida (blacklist) o refresh token
    enviado no corpo da requisição: {"refresh": "<token>"}.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'logout'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh_token:
            return Response(
                {'detail': 'Cookie de atualização ausente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(refresh_token)
            if str(refresh[api_settings.USER_ID_CLAIM]) != str(request.user.pk):
                return Response({'detail': 'Token de atualização inválido.'}, status=status.HTTP_400_BAD_REQUEST)
            refresh.blacklist()
        except (KeyError, TokenError):
            return Response(
                {'detail': 'Token inválido ou já expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            path=settings.JWT_REFRESH_COOKIE_PATH,
            samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        )
        return response


class RegistrationView(APIView):
    """POST /api/v1/auth/register/ — cria uma conta inicial de cliente."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = 'register'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        serializer = PublicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class PasswordChangeView(APIView):
    """POST /auth/password/change/ — troca a senha da sessão autenticada."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'password_change'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            path=settings.JWT_REFRESH_COOKIE_PATH,
            samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        )
        return response


class PasswordResetRequestView(APIView):
    """POST /auth/password/reset/ — inicia recuperação sem revelar contas."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(APIView):
    """POST /auth/password/reset/confirm/ — confirma token e define senha nova."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset_confirm'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            path=settings.JWT_REFRESH_COOKIE_PATH,
            samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        )
        return response


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
        if user.barbershop_id is None:
            return queryset.none()
        return queryset.filter(barbershop_id=user.barbershop_id)

    def perform_destroy(self, instance):
        # A remoção pela API desativa a conta, preservando agendamentos e
        # demais registros históricos vinculados ao usuário.
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        # Tokens de refresh emitidos antes da desativação não podem renovar
        # a sessão. O access token existente expira no prazo curto definido.
        revoke_user_refresh_tokens(instance)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/v1/users/me/ — dados do usuário autenticado."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
