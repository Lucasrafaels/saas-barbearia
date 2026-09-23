"""
Views do app barbershops.
"""
from django.db import transaction
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
        if self.action == 'list' and 'ativo' not in self.request.query_params:
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
            barber = serializer.save(
                user=user,
                barbershop_id=self.request.user.barbershop_id,
            )
            if user.tipo_perfil != user.TipoPerfil.BARBEIRO:
                user.tipo_perfil = user.TipoPerfil.BARBEIRO
                user.save(update_fields=['tipo_perfil'])
            return barber

    def perform_destroy(self, instance):
        # O histórico de agendamentos permanece consultável; a conta volta a
        # ser cliente e não conserva um papel de barbeiro sem perfil ativo.
        with transaction.atomic():
            if instance.agendamentos.exists():
                conflict = APIException('Não é possível excluir um barbeiro com agendamentos no histórico.')
                conflict.status_code = 409
                raise conflict
            instance.ativo = False
            instance.save(update_fields=['ativo'])
            user = instance.user
            if user.tipo_perfil == user.TipoPerfil.BARBEIRO:
                user.tipo_perfil = user.TipoPerfil.CLIENTE
                user.save(update_fields=['tipo_perfil'])
