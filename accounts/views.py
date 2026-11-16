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
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
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
    admin_integrity_error_as_drf,
    revoke_user_refresh_tokens,
)
from .admin_integrity import AdminIntegrityError, check_self_change
from .throttles import (
    LIMITES_DE_CRIACAO_DE_USUARIO,
    LIMITES_DE_TROCA_DE_EMAIL,
    CadastroPublicoPorDiaThrottle,
    tenta_trocar_email,
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
    # TEN-03 (mitigação D): o limite por hora (`register`) já existia. O
    # diário reduz a sondagem contínua de e-mails a partir da mesma origem. Os
    # dois contam toda tentativa, válida ou não, antes da validação.
    throttle_classes = [ScopedRateThrottle, CadastroPublicoPorDiaThrottle]

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

    def get_throttles(self):
        # TEN-03 (mitigação D): a criação consulta a unicidade do e-mail em
        # toda a plataforma. O DRF checa estes limites depois da permissão
        # (só administradores chegam aqui) e antes da validação. Esgotada a
        # cota, nenhuma tentativa chega a consultar o e-mail.
        throttles = super().get_throttles()
        if self.action == 'create':
            throttles += [limite() for limite in LIMITES_DE_CRIACAO_DE_USUARIO]
        return throttles

    def update(self, request, *args, **kwargs):
        """
        Igual ao `UpdateModelMixin.update`, com o limite da troca de e-mail
        entre a busca e a validação (TEN-03, mitigação D).

        A busca (`get_object`) vem primeiro e mantém o escopo e as respostas
        atuais: 404 fora do alcance e 403 do SEC-12, sem gastar a cota. Só um
        pedido que tenta gravar um e-mail diferente do atual conta no limite de
        quem pede. Esgotado o limite, a resposta é 429, sem consultar a
        unicidade.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if tenta_trocar_email(request.data, instance):
            self._aplicar_limites(request, LIMITES_DE_TROCA_DE_EMAIL)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def _aplicar_limites(self, request, classes):
        """Mesma regra do `APIView.check_throttles`, para limites checados depois da busca."""
        esperas = []
        for classe in classes:
            limite = classe()
            if not limite.allow_request(request, self):
                esperas.append(limite.wait())
        if esperas:
            esperas = [espera for espera in esperas if espera is not None]
            self.throttled(request, max(esperas, default=None))

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_superuser:
            return queryset
        if user.barbershop_id is None:
            return queryset.none()
        queryset = queryset.filter(barbershop_id=user.barbershop_id)
        if self.action == 'retrieve' and user.tipo_perfil != User.TipoPerfil.ADMIN:
            # PER-13 (SEC-10): na leitura de detalhe (GET e HEAD), cliente e
            # barbeiro só enxergam o próprio cadastro, já na consulta. Antes, o
            # registro de outro usuário da barbearia era lido e recusado por
            # IsSelfOrAdmin (403), enquanto o de outra barbearia ou inexistente
            # dava 404: a diferença revelava quais IDs existem. Agora todos dão
            # o mesmo 404, sem carregar o registro. A própria conta continua
            # disponível aqui e em /users/me/. As escritas não mudaram (SEC-12).
            queryset = queryset.filter(pk=user.pk)
        return queryset

    def perform_destroy(self, instance):
        # A remoção pela API desativa a conta, preservando agendamentos e
        # demais registros históricos vinculados ao usuário.
        # Se o usuário for barbeiro, também desativa o perfil Barber.
        from django.db import transaction

        try:
            # O DELETE da API é uma desativação; a regra do último admin
            # ativo é imposta por User.save().
            check_self_change(self.request.user, instance, is_active=False)
            with transaction.atomic():
                self._deactivate(instance)
        except AdminIntegrityError as error:
            raise admin_integrity_error_as_drf(error, key='detail') from error

    def _deactivate(self, instance):
        from django.utils import timezone
        from barbershops.models import Barber

        instance.is_active = False
        instance.save(update_fields=['is_active'])
        # Tokens de refresh emitidos antes da desativação não podem renovar
        # a sessão. O access token existente expira no prazo curto definido.
        revoke_user_refresh_tokens(instance)

        # Desativar perfil de barbeiro se existir
        try:
            barber = instance.perfil_barbeiro
            if barber.ativo:
                barber.ativo = False
                barber.deleted_at = timezone.now()
                barber.deleted_by = self.request.user
                barber.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
        except Barber.DoesNotExist:
            pass

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/v1/users/me/ — dados do usuário autenticado."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
