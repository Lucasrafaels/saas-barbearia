"""
Modelo de usuário customizado do sistema.

Cada usuário tem um tipo de perfil (admin/barbeiro/cliente) e pertence a
uma barbearia — esse campo `barbershop` é a base de toda a arquitetura
multi-tenant do projeto: a maioria das queries do sistema é filtrada por
`barbershop_id` (ver config.mixins.TenantScopedQuerysetMixin).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from config.models import TimeStampedModel
from .managers import UserManager


class User(AbstractUser, TimeStampedModel):
    class TipoPerfil(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        BARBEIRO = 'barbeiro', 'Barbeiro'
        CLIENTE = 'cliente', 'Cliente'

    # Removemos os campos padrão do Django que não usamos, para que o
    # modelo reflita exatamente os campos pedidos (email, nome, tipo_perfil).
    username = None
    first_name = None
    last_name = None

    email = models.EmailField('e-mail', unique=True)
    nome = models.CharField('nome completo', max_length=150)
    tipo_perfil = models.CharField(
        'tipo de perfil',
        max_length=10,
        choices=TipoPerfil.choices,
        default=TipoPerfil.CLIENTE,
    )
    # Barbearia à qual o usuário pertence. Nullable porque um admin da
    # plataforma (superuser, equipe interna) pode não estar vinculado a
    # nenhuma barbearia específica.
    barbershop = models.ForeignKey(
        'barbershops.Barbershop',
        verbose_name='barbearia',
        related_name='usuarios',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = UserManager()

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_perfil_display()})'

    # AbstractUser.get_full_name/get_short_name usam first_name/last_name
    # por padrão; como removemos esses campos, sobrescrevemos aqui para
    # que qualquer código do Django (ex.: admin) continue funcionando.
    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome

    @property
    def is_admin(self):
        return self.tipo_perfil == self.TipoPerfil.ADMIN

    @property
    def is_barbeiro(self):
        return self.tipo_perfil == self.TipoPerfil.BARBEIRO

    @property
    def is_cliente(self):
        return self.tipo_perfil == self.TipoPerfil.CLIENTE
