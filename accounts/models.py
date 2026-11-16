"""
Modelo de usuário customizado do sistema.

Cada usuário tem um tipo de perfil (admin/barbeiro/cliente) e pertence a
uma barbearia — esse campo `barbershop` é a base de toda a arquitetura
multi-tenant do projeto: a maioria das queries do sistema é filtrada por
`barbershop_id` (ver core.mixins.TenantScopedQuerysetMixin).
"""
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from config.models import TimeStampedModel
from .admin_integrity import GUARDED_FIELDS, active_admin_barbershop, preserving_active_admins
from .emails import (
    EXPRESSAO_SQL_DA_FAIXA,
    RESTRICAO_CHECK,
    RESTRICAO_UNIQUE_LOWER,
    normalizar_email,
)
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
        on_delete=models.PROTECT,
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
        # AUTH-04/AUTH-05 (accounts.emails, migração 0006): o banco garante a
        # regra única do e-mail mesmo nos caminhos que não passam por save(),
        # como QuerySet.update(), bulk_create(), SQL e pedidos simultâneos. O
        # unique=True do campo continua: o check auth.E003 exige unicidade no
        # próprio USERNAME_FIELD, e uma restrição funcional não conta.
        constraints = [
            models.CheckConstraint(
                check=Q(email=Lower('email')) & Q(email__regex=EXPRESSAO_SQL_DA_FAIXA),
                name=RESTRICAO_CHECK,
            ),
            models.UniqueConstraint(Lower('email'), name=RESTRICAO_UNIQUE_LOWER),
        ]

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_perfil_display()})'

    def clean(self):
        """
        Aplica a regra única do e-mail (accounts.emails) na validação de modelo (Django Admin).

        Substitui os `clean()` herdados. O `AbstractBaseUser.clean()` aplica
        NFKC ao USERNAME_FIELD, o que transformaria caracteres Unicode (letras
        de largura total, por exemplo) em ASCII **antes** da checagem da faixa.
        O `AbstractUser.clean()` só punha o domínio em minúsculas.
        """
        try:
            self.email = normalizar_email(self.email)
        except ValidationError as erro:
            raise ValidationError({'email': erro.error_list}) from erro

    def validate_constraints(self, exclude=None):
        """
        Não repete, na validação de modelo, as duas restrições do e-mail (CHECK e UNIQUE (LOWER(email))).

        Elas já estão garantidas antes daqui. O `clean()` grava a forma
        canônica, e o `unique=True` do campo recusa a duplicata com a mensagem
        de sempre, porque, na forma canônica, igualdade exata equivale a
        UNIQUE (LOWER(email)). Validá-las de novo só acrescentava, no Django
        Admin, um segundo erro com o nome interno da restrição. O banco
        continua sendo a garantia final.
        """
        super().validate_constraints(exclude={*(exclude or ()), 'email'})

    # AbstractUser.get_full_name/get_short_name usam first_name/last_name
    # por padrão; como removemos esses campos, sobrescrevemos aqui para
    # que qualquer código do Django (ex.: admin) continue funcionando.
    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome

    # BUS-01: uma barbearia com admin ativo nunca fica sem nenhum, qualquer
    # que seja o caminho (API, Django Admin, shell). Ver accounts.admin_integrity.
    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        # AUTH-05: o e-mail gravado está sempre na forma canônica. Se o valor
        # não couber na regra, a gravação é recusada com ValidationError. Só
        # quando o e-mail é gravado: um save(update_fields=['last_login']), por
        # exemplo, não depende dele.
        if update_fields is None or 'email' in update_fields:
            self.email = normalizar_email(self.email)
        if (
            self._state.adding
            or self.pk is None
            or (update_fields is not None and GUARDED_FIELDS.isdisjoint(update_fields))
        ):
            return super().save(*args, **kwargs)
        origin = active_admin_barbershop(self.pk)
        still_admin_there = (
            self.tipo_perfil == self.TipoPerfil.ADMIN
            and self.is_active
            and self.barbershop_id == origin
        )
        if origin is None or still_admin_there:
            return super().save(*args, **kwargs)
        with preserving_active_admins({origin}):
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        origin = active_admin_barbershop(self.pk) if self.pk else None
        if origin is None:
            return super().delete(*args, **kwargs)
        with preserving_active_admins({origin}):
            return super().delete(*args, **kwargs)

    @property
    def is_admin(self):
        return self.tipo_perfil == self.TipoPerfil.ADMIN

    @property
    def is_barbeiro(self):
        return self.tipo_perfil == self.TipoPerfil.BARBEIRO

    @property
    def is_cliente(self):
        return self.tipo_perfil == self.TipoPerfil.CLIENTE
