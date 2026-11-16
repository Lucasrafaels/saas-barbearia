"""
Manager customizado para o modelo User, que usa e-mail (em vez do
username padrão do Django) como identificador principal de login.
"""
from django.contrib.auth.base_user import BaseUserManager
from django.db import models

from .admin_integrity import GUARDED_FIELDS, preserving_active_admins
from .emails import forma_canonica, normalizar_email


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

    @classmethod
    def normalize_email(cls, email):
        """
        Regra única do e-mail (accounts.emails), no lugar da do Django, que só
        punha o domínio em minúsculas (AUTH-05). Vale para `create_user` e
        `create_superuser`. Valor fora da regra: `ValidationError`.
        """
        return normalizar_email(email)

    def get_by_natural_key(self, username):
        """
        Busca pela forma canônica e com igualdade exata.

        É o que o `ModelBackend` usa no login da API, no login do Django Admin
        e no `createsuperuser`. Por isso o login não diferencia caixa e não
        precisa mudar nas views (AUTH-05). Um valor fora da regra se comporta
        como conta inexistente: o `ModelBackend` mantém a mesma proteção de
        tempo e a mesma resposta.
        """
        email = forma_canonica(username)
        if email is None:
            raise self.model.DoesNotExist('Nenhuma conta com esse e-mail.')
        return self.get(**{self.model.USERNAME_FIELD: email})

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
