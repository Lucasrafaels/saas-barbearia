"""
Formulários customizados para o Django Admin.

Necessários porque UserCreationForm/UserChangeForm padrão do Django
referenciam o campo "username", que não existe no nosso User customizado
(usamos e-mail como identificador). Este é o padrão recomendado pela
própria documentação do Django ao trocar o USERNAME_FIELD.
"""
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'nome', 'tipo_perfil', 'barbershop')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
