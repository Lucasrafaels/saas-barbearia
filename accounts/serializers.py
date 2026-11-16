"""
Serializers do app accounts.
"""
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.utils.field_mapping import get_unique_error_message

from .admin_integrity import AdminIntegrityError, check_self_change, lock_active_admins
from .emails import e_violacao_da_unicidade_do_email, forma_canonica
from .models import User


class EmailNormalizadoField(serializers.EmailField):
    """
    `EmailField` que entrega o valor já na forma canônica (accounts.emails).

    A normalização precisa estar aqui, e não num `validate_email`. O DRF roda os
    validadores do campo, inclusive o `UniqueValidator`, dentro de
    `run_validation`, logo depois deste `to_internal_value` e **antes** do
    `validate_<campo>` do serializer. Assim, a checagem de duplicidade já
    compara a forma canônica.

    A resposta para entrada inválida é a mesma de antes. Um valor que não é
    texto recebe 'invalid' sem conversão de tipo; `null` e vazio continuam a
    cargo do DRF ('null' e 'blank'). Um texto fora da regra também recebe
    'invalid'.
    """

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid')
        canonico = forma_canonica(super().to_internal_value(data))
        if canonico is None:
            self.fail('invalid')
        return canonico


class EmailCanonicoMixin:
    """Faz os ModelSerializers de usuário gerarem o campo `email` como `EmailNormalizadoField`."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.EmailField: EmailNormalizadoField,
    }


def recusar_email_duplicado(erro):
    """
    Pedido simultâneo: os dois passaram pelo `UniqueValidator`, mas o banco
    recusou o segundo. Responde o mesmo 400 que o validador daria. Qualquer
    outro `IntegrityError` é levantado de novo, sem ser mascarado.
    """
    if e_violacao_da_unicidade_do_email(erro):
        mensagem = get_unique_error_message(User._meta.get_field('email'))
        raise serializers.ValidationError({'email': [serializers.ErrorDetail(mensagem, code='unique')]}) from erro
    raise erro


def revoke_user_refresh_tokens(user):
    """Invalida refresh tokens já emitidos para encerrar sessões do usuário."""
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken, OutstandingToken,
    )

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def admin_integrity_error_as_drf(error, key=None):
    """Converte AdminIntegrityError (regra do modelo) em erro 400 da API."""
    if key is None and hasattr(error, 'error_dict'):
        return serializers.ValidationError(error.message_dict)
    return serializers.ValidationError({key or 'detail': error.messages})


class UserSerializer(EmailCanonicoMixin, serializers.ModelSerializer):
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
            self.fields['is_active'].read_only = True

    def validate_tipo_perfil(self, value):
        # Mesma regra já aplicada na criação (UserCreateSerializer): este
        # endpoint genérico nunca é o caminho para conceder papel de
        # administrador, nem para um admin promover alguém a admin.
        if value == User.TipoPerfil.ADMIN:
            raise serializers.ValidationError(
                'Não é possível definir o papel de administrador por este endpoint.'
            )
        return value

    def validate(self, attrs):
        # Ninguém altera o próprio papel nem desativa a própria conta por
        # aqui: para um admin, as duas operações tiram o acesso
        # administrativo de quem está executando a ação.
        request = self.context.get('request')
        if self.instance is not None:
            try:
                check_self_change(
                    getattr(request, 'user', None), self.instance,
                    tipo_perfil=attrs.get('tipo_perfil'), is_active=attrs.get('is_active'),
                )
            except AdminIntegrityError as error:
                raise admin_integrity_error_as_drf(error) from error
        if (
            self.instance is not None
            and self.instance.tipo_perfil == User.TipoPerfil.ADMIN
            and attrs.get('tipo_perfil') == User.TipoPerfil.BARBEIRO
        ):
            raise serializers.ValidationError({
                'tipo_perfil': 'Usuários administradores não podem ser convertidos em barbeiros.'
            })
        return super().validate(attrs)

    def update(self, instance, validated_data):
        # A regra do último admin ativo é imposta por User.save().
        try:
            return self._apply_update(instance, validated_data)
        except AdminIntegrityError as error:
            raise admin_integrity_error_as_drf(error, key='detail') from error
        except IntegrityError as erro:
            # AUTH-05: _apply_update roda em transaction.atomic(). O erro chega
            # aqui com a transação desfeita até esse ponto e íntegra.
            recusar_email_duplicado(erro)

    def _apply_update(self, instance, validated_data):
        """Atualiza campos permitidos. Alteração de papel (tipo_perfil) sincroniza
        automaticamente o perfil de Barber para manter consistência.
        """
        # Capture is_active before popping to detect deactivation
        is_active_value = validated_data.pop('is_active', None)
        is_being_deactivated = (
            instance.is_active
            and is_active_value is False
        )
        is_being_activated = (
            not instance.is_active
            and is_active_value is True
        )

        new_role = validated_data.pop('tipo_perfil', None)
        removes_admin_access = (
            instance.tipo_perfil == User.TipoPerfil.ADMIN
            and (
                (new_role is not None and new_role != User.TipoPerfil.ADMIN)
                or is_active_value is False
            )
        )
        with transaction.atomic():
            # A trava dos admins vem antes da trava do próprio usuário, na
            # mesma ordem que User.save() usa. Sem isso, dois admins
            # rebaixando um ao outro ao mesmo tempo poderiam entrar em deadlock.
            if removes_admin_access:
                lock_active_admins({instance.barbershop_id})
            instance = type(instance).objects.select_for_update().get(pk=instance.pk)
            old_role = instance.tipo_perfil

            # Handle role change with Barber profile sync
            if new_role is not None and new_role != old_role:
                from barbershops.models import Barber
                # Demote from BARBEIRO -> deactivate Barber profile
                if old_role == User.TipoPerfil.BARBEIRO:
                    try:
                        barber = instance.perfil_barbeiro
                        barber.ativo = False
                        barber.deleted_at = timezone.now()
                        request = self.context.get('request')
                        barber.deleted_by = getattr(request, 'user', None)
                        barber.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
                    except Barber.DoesNotExist:
                        pass
                # Promote to BARBEIRO -> create or activate Barber profile
                if new_role == User.TipoPerfil.BARBEIRO:
                    barber, created = Barber.objects.get_or_create(
                        user=instance,
                        defaults={'barbershop': instance.barbershop, 'ativo': True}
                    )
                    if not created and not barber.ativo:
                        barber.ativo = True
                        barber.deleted_at = None
                        barber.deleted_by = None
                        barber.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
                instance.tipo_perfil = new_role

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Apply is_active change if provided
            if is_active_value is not None:
                instance.is_active = is_active_value
            instance.save()

            # Sync Barber profile when is_active changes
            if is_being_deactivated:
                from barbershops.models import Barber
                try:
                    barber = instance.perfil_barbeiro
                    barber.ativo = False
                    barber.deleted_at = timezone.now()
                    request = self.context.get('request')
                    barber.deleted_by = getattr(request, 'user', None)
                    barber.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
                except Barber.DoesNotExist:
                    pass
            # NOTE: Reactivating user (is_being_activated) does NOT auto-reactivate
            # the Barber profile. The Barber profile must be explicitly reactivated
            # by an administrator through the Barber API to avoid unintentional
            # reactivation of professionals who were manually deactivated.

            if is_being_deactivated:
                revoke_user_refresh_tokens(instance)
        return instance


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


class UserCreateSerializer(EmailCanonicoMixin, PasswordValidationMixin, serializers.ModelSerializer):
    """Serializer usado para cadastro de novos usuários (recebe senha)."""

    password = serializers.CharField(write_only=True, min_length=8)
    # Campos opcionais para criar o perfil de Barber junto com o usuário
    especialidade = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=100)
    ativo = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'password', 'tipo_perfil', 'barbershop', 'especialidade', 'ativo']
        read_only_fields = ['id', 'barbershop']

    def validate_tipo_perfil(self, value):
        if value == User.TipoPerfil.ADMIN:
            raise serializers.ValidationError(
                'Administradores não podem ser criados por este endpoint.'
            )
        return value

    def validate(self, attrs):
        # Se tipo_perfil for BARBEIRO, especialidade é obrigatória
        if attrs.get('tipo_perfil') == User.TipoPerfil.BARBEIRO:
            if not attrs.get('especialidade'):
                raise serializers.ValidationError(
                    {'especialidade': 'Este campo é obrigatório para usuários do tipo barbeiro.'}
                )
        return super().validate(attrs)

    def create(self, validated_data):
        password = validated_data.pop('password')
        especialidade = validated_data.pop('especialidade', None)
        barber_active = validated_data.pop('ativo', True)
        request = self.context.get('request')
        if not request or not request.user.barbershop_id:
            raise serializers.ValidationError(
                {'barbershop': 'O administrador precisa pertencer a uma barbearia.'}
            )
        # Defesa em profundidade: apenas ADMIN (ou superuser) pode criar usuários.
        # A permissão IsAdminRole no ViewSet já bloqueia, mas validamos aqui também.
        requester = request.user
        is_admin = bool(
            requester.is_authenticated
            and (requester.is_superuser or requester.tipo_perfil == User.TipoPerfil.ADMIN)
        )
        if not is_admin:
            raise serializers.ValidationError(
                {'detail': 'Apenas administradores podem criar usuários.'}
            )

        is_barber = validated_data.get('tipo_perfil') == User.TipoPerfil.BARBEIRO
        # O papel BARBEIRO representa acesso profissional vigente. Um perfil
        # criado já inativo fica registrado para o histórico, mas a conta
        # permanece CLIENTE até que ele seja reativado.
        if is_barber and not barber_active:
            validated_data['tipo_perfil'] = User.TipoPerfil.CLIENTE

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    barbershop=request.user.barbershop,
                    **validated_data,
                )

                if is_barber:
                    from barbershops.models import Barber
                    barber = Barber(
                        user=user,
                        barbershop=request.user.barbershop,
                        especialidade=especialidade or '',
                        ativo=barber_active,
                    )
                    # create()/save() não chama clean() automaticamente no
                    # Django. Validamos explicitamente para preservar as regras
                    # de tenant e de perfil também neste fluxo composto.
                    try:
                        barber.full_clean()
                    except DjangoValidationError as error:
                        raise serializers.ValidationError(error.message_dict) from error
                    if not barber_active:
                        barber.deleted_at = timezone.now()
                        barber.deleted_by = request.user
                    barber.save()
        except IntegrityError as erro:
            # AUTH-05: pedido simultâneo com o mesmo e-mail. O atomic() acima já
            # desfez esta criação, e a transação externa continua íntegra.
            recusar_email_duplicado(erro)

        return user


class PublicRegistrationSerializer(EmailCanonicoMixin, PasswordValidationMixin, serializers.ModelSerializer):
    """Cadastro público inicial, sempre criado como cliente sem tenant."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        try:
            with transaction.atomic():
                return User.objects.create_user(password=password, **validated_data)
        except IntegrityError as erro:
            # AUTH-05: cadastro simultâneo com o mesmo e-mail (o banco recusa o
            # segundo). Mesmo 400 do UniqueValidator, sem 500.
            recusar_email_duplicado(erro)


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


class ActiveUserTokenRefreshSerializer(TokenRefreshSerializer):
    """Não renova sessões de contas removidas, inativas ou inexistentes."""

    def validate(self, attrs):
        try:
            token = RefreshToken(attrs['refresh'])
            user_id = token[api_settings.USER_ID_CLAIM]
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (KeyError, User.DoesNotExist, TokenError, ValueError, TypeError) as error:
            raise AuthenticationFailed('Token de atualização inválido.') from error

        if not user.is_active:
            raise AuthenticationFailed('Conta de usuário inativa.')
        return super().validate(attrs)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Senha atual incorreta.')
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs['new_password'], user=self.context['request'].user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': error.messages}) from error
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        with transaction.atomic():
            user.set_password(self.validated_data['new_password'])
            user.save(update_fields=['password'])
            revoke_user_refresh_tokens(user)
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    # AUTH-04: o e-mail chega na forma canônica (accounts.emails).
    email = EmailNormalizadoField()

    def save(self, **kwargs):
        # A resposta é idêntica para e-mails existentes e inexistentes, para
        # não transformar este endpoint em uma fonte de enumeração de contas.
        # O envio é SEMPRE tentado (mesmo para e-mail inexistente) para evitar
        # timing attack: a latência deve ser constante independentemente da
        # existência da conta. Em produção, usar Celery para envio assíncrono.
        email = self.validated_data['email']
        # AUTH-04: igualdade exata com a forma canônica, que o banco mantém
        # única (accounts.0006). Antes era `email__iexact` + `.first()` pela
        # ordem do nome, e uma conta com outra caixa podia ser escolhida no
        # lugar da certa.
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            user = None

        # Sempre preparar dados do e-mail (mesmo se user for None)
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            recipient_list = [user.email]
        else:
            # Dados fictícios para manter latência constante
            uid = urlsafe_base64_encode(force_bytes(0))
            token = 'dummy-token'
            recipient_list = [settings.DEFAULT_FROM_EMAIL]  # nunca entregue

        try:
            send_mail(
                subject='Recuperação de senha',
                message=(
                    'Use estes dados para redefinir sua senha:\n\n'
                    f'uid: {uid}\n'
                    f'token: {token}\n\n'
                    'Se você não solicitou a alteração, ignore esta mensagem.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True,  # não vazar erro de SMTP
            )
        except Exception:
            # Log interno em produção; nunca propagar para o cliente
            pass


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as error:
            raise serializers.ValidationError({'token': 'Token inválido ou expirado.'}) from error

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': 'Token inválido ou expirado.'})
        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': error.messages}) from error
        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        with transaction.atomic():
            user.set_password(self.validated_data['new_password'])
            user.save(update_fields=['password'])
            revoke_user_refresh_tokens(user)
        return user
