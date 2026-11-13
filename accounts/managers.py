"""
Manager customizado para o modelo User, que usa e-mail (em vez do
username padrão do Django) como identificador principal de login.
"""
from django.contrib.auth.base_user import BaseUserManager
from django.db import models

from .admin_integrity import GUARDED_FIELDS, preserving_active_admins


class UserQuerySet(models.QuerySet):
    """Operações em lote também respeitam a regra do último admin ativo (BUS-01).

    `QuerySet.update()` e `QuerySet.delete()` não passam por `User.save()` nem
    por `User.delete()`. São usadas, por exemplo, pela ação "remover
    selecionados" do Django Admin e por `bulk_update()`.
    """

    def _active_admin_barbershops(self):
        return set(
            self.filter(tipo_perfil='admin', is_active=True).values_list('barbershop_id', flat=True)
        )

    def update(self, **kwargs):
        if GUARDED_FIELDS.isdisjoint(kwargs):
            return super().update(**kwargs)
        with preserving_active_admins(self._active_admin_barbershops()):
            return super().update(**kwargs)

    def delete(self):
        with preserving_active_admins(self._active_admin_barbershops()):
            return super().delete()


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    """Gerencia a criação de usuários e superusuários usando e-mail."""

    use_in_migrations = True

    def create_user(self, email, nome, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_perfil', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa ter is_superuser=True.')

        return self.create_user(email, nome, password, **extra_fields)
