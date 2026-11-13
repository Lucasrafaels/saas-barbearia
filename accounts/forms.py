"""
Formulários customizados para o Django Admin.

Necessários porque UserCreationForm/UserChangeForm padrão do Django
referenciam o campo "username", que não existe no nosso User customizado
(usamos e-mail como identificador). Este é o padrão recomendado pela
própria documentação do Django ao trocar o USERNAME_FIELD.
"""
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .admin_integrity import check_admin_removal, check_self_change
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'nome', 'tipo_perfil', 'barbershop')


class CustomUserChangeForm(UserChangeForm):
    # Preenchido pelo UserAdmin com o usuário logado (regra de autoalteração).
    actor = None

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def clean(self):
        """Antecipa no formulário as regras do BUS-01 (ver accounts.admin_integrity).

        Aqui `self.instance` ainda tem os valores gravados: o Django só copia o
        formulário para a instância depois de clean(). A garantia definitiva,
        inclusive sob concorrência, é User.save().
        """
        cleaned_data = super().clean()
        user = self.instance
        if user.pk is None:
            return cleaned_data
        tipo_perfil = cleaned_data.get('tipo_perfil', user.tipo_perfil)
        is_active = cleaned_data.get('is_active', user.is_active)
        barbershop = cleaned_data.get('barbershop', user.barbershop)
        check_self_change(self.actor, user, tipo_perfil=tipo_perfil, is_active=is_active)
        leaves_admin_role = not (
            tipo_perfil == User.TipoPerfil.ADMIN
            and is_active
            and getattr(barbershop, 'pk', None) == user.barbershop_id
        )
        if leaves_admin_role:
            check_admin_removal([user.pk])
        return cleaned_data
