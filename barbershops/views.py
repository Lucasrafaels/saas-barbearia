"""
Views do app barbershops.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied

from config.mixins import TenantScopedQuerysetMixin
from config.permissions import IsAdminRole
from .models import Barber, Barbershop
from .serializers import BarberSerializer, BarbershopSerializer


class BarbershopViewSet(viewsets.ModelViewSet):
    """
    Gestão da barbearia (o tenant). Um usuário comum só enxerga a
    própria barbearia; superusuários (equipe interna da plataforma)
    enxergam todas — útil para suporte/onboarding de novos clientes.
    """
    queryset = Barbershop.objects.all()
    serializer_class = BarbershopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        return super().get_queryset().filter(id=user.barbershop_id)

    def get_permissions(self):
        # Criar é o fluxo de onboarding: qualquer usuário autenticado sem
        # barbearia ainda pode criar a sua (e vira admin dela, ver
        # perform_create). Destruir continua restrito à equipe da
        # plataforma (staff do Django admin).
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        barbershop = serializer.save()
        user = self.request.user
        # O usuário que cria a barbearia passa a ser o admin dela. A
        # ausência de tenant já foi garantida em
        # BarbershopSerializer.validate(), então não há mais o branch
        # silencioso que deixava a barbearia órfã.
        user.barbershop = barbershop
        user.tipo_perfil = user.TipoPerfil.ADMIN
        user.save(update_fields=['barbershop', 'tipo_perfil'])

    def perform_destroy(self, instance):
        # DELETE mantém o contrato HTTP do frontend, mas não permite que uma
        # única chamada apague todo o tenant por cascata.
        confirmation = self.request.query_params.get('confirmar')
        if confirmation != instance.nome:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'confirmar': 'Informe exatamente o nome da barbearia para confirmar a exclusão.'})
        # Preserva usuários, agenda e financeiro vinculados por FKs PROTECT.
        # A confirmação impede que uma chamada acidental desative o tenant.
        instance.ativo = False
        instance.save(update_fields=['ativo'])


class BarberViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Gestão dos barbeiros da barbearia do usuário autenticado. Leitura
    liberada para qualquer usuário autenticado da barbearia (ex.: um
    cliente precisa ver a lista de barbeiros para agendar); escrita
    restrita a administradores.
    """
    queryset = Barber.objects.select_related('user', 'barbershop').all()
    serializer_class = BarberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtro por status ativo/inativo:
        # - Sem parâmetro (público) → apenas ativos
        # - ativo=true → apenas ativos
        # - ativo=false → apenas inativos
        # - ativo=all (apenas admin/superuser) → todos (sem filtro)
        ativo_param = self.request.query_params.get('ativo')
        user = self.request.user

        # Superuser pode ver todos os barbeiros independentemente do filtro
        # Para operações de escrita (UPDATE, DELETE), superuser vê todos
        # independentemente do status ativo para permitir reativação/exclusão
        is_write_operation = self.action in ['update', 'partial_update', 'destroy']
        if user.is_authenticated and user.is_superuser:
            if ativo_param == 'all' or is_write_operation:
                return queryset  # Todos
            elif ativo_param == 'false':
                return queryset.filter(ativo=False)
            elif ativo_param == 'true':
                return queryset.filter(ativo=True)
            else:
                return queryset.filter(ativo=True)  # Padrão: apenas ativos

        # Para operações de escrita (UPDATE, DELETE), admins devem poder
        # acessar barbeiros inativos para reativar ou confirmar exclusão.
        # A permissão IsAdminRole já garante que só admins chegam aqui.
        is_write_operation = self.action in ['update', 'partial_update', 'destroy']

        if ativo_param == 'all':
            # Apenas admins podem ver inativos via ativo=all
            if user.is_authenticated and user.tipo_perfil == 'admin':
                # Admin explícito: retorna todos, sem filtro por ativo
                pass
            else:
                # Não-admins: ignora ativo=all e usa padrão (apenas ativos)
                queryset = queryset.filter(ativo=True)
        elif ativo_param == 'false':
            # Apenas admins podem filtrar inativos
            if user.is_authenticated and user.tipo_perfil == 'admin':
                queryset = queryset.filter(ativo=False)
            else:
                # Não-admins não podem ver inativos
                queryset = queryset.filter(ativo=True)
        else:
            # ativo=true ou parâmetro ausente (padrão público)
            # Mas para operações de escrita de admin, não filtramos por ativo
            # para permitir reativação e exclusão de inativos
            if is_write_operation and user.is_authenticated and user.tipo_perfil == 'admin':
                pass  # Admin em operação de escrita vê todos
            else:
                queryset = queryset.filter(ativo=True)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_superuser and self.request.user.barbershop_id is None:
            raise PermissionDenied(
                'Selecione um contexto de barbearia antes de criar recursos de tenant.'
            )
        with transaction.atomic():
            user = serializer.validated_data['user']
            # Serializa promoções concorrentes para o mesmo usuário e evita
            # confirmar um Barber vinculado a um papel incompatível.
            user = type(user).objects.select_for_update().get(pk=user.pk)
            will_be_active = serializer.validated_data.get('ativo', True)
            # A alteração do papel acontece antes do save do Barber, mas as
            # duas escritas pertencem à mesma transação. Se o perfil falhar,
            # a promoção também é desfeita.
            if will_be_active and user.tipo_perfil != user.TipoPerfil.BARBEIRO:
                user.tipo_perfil = user.TipoPerfil.BARBEIRO
                user.save(update_fields=['tipo_perfil'])
            barber = serializer.save(
                user=user,
                barbershop_id=self.request.user.barbershop_id,
            )
            return barber

    def perform_destroy(self, instance):
        # O histórico de agendamentos permanece consultável; a conta volta a
        # ser cliente e não conserva um papel de barbeiro sem perfil ativo.
        with transaction.atomic():
            instance.ativo = False
            instance.deleted_at = timezone.now()
            instance.deleted_by = self.request.user
            instance.save(update_fields=['ativo', 'deleted_at', 'deleted_by'])
            user = instance.user
            if user.tipo_perfil == user.TipoPerfil.BARBEIRO:
                user.tipo_perfil = user.TipoPerfil.CLIENTE
                user.save(update_fields=['tipo_perfil'])

    def perform_update(self, serializer):
        """Mantém papel, soft-delete e atividade do perfil sincronizados."""
        with transaction.atomic():
            # Lock the user row to serialize concurrent updates
            user = serializer.instance.user
            user = type(user).objects.select_for_update().get(pk=user.pk)

            # Check if we're deactivating (ativo: True -> False)
            was_active = serializer.instance.ativo
            will_be_active = serializer.validated_data.get('ativo', serializer.instance.ativo)

            barber = serializer.save()

            if not will_be_active:
                # A desativação por PATCH tem a mesma semântica do DELETE
                # lógico: conserva agenda/histórico e remove o papel ativo.
                if user.tipo_perfil != user.TipoPerfil.CLIENTE:
                    user.tipo_perfil = user.TipoPerfil.CLIENTE
                    user.save(update_fields=['tipo_perfil'])
                if barber.deleted_at is None:
                    barber.deleted_at = timezone.now()
                    barber.deleted_by = self.request.user
                    barber.save(update_fields=['deleted_at', 'deleted_by'])
            else:
                # Tanto a reativação como uma correção de estado legado
                # restauram o único papel compatível com um Barber ativo.
                if user.tipo_perfil != user.TipoPerfil.BARBEIRO:
                    user.tipo_perfil = user.TipoPerfil.BARBEIRO
                    user.save(update_fields=['tipo_perfil'])
                if barber.deleted_at or barber.deleted_by:
                    barber.deleted_at = None
                    barber.deleted_by = None
                    barber.save(update_fields=['deleted_at', 'deleted_by'])

            return barber
