"""
Registro do modelo User no Django Admin.P
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    ordering = ['email']
    list_display = ['email', 'nome', 'tipo_perfil', 'barbershop', 'is_active', 'is_staff']
    list_filter = ['tipo_perfil', 'barbershop', 'is_active', 'is_staff']
    search_fields = ['email', 'nome']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações pessoais', {'fields': ('nome', 'tipo_perfil', 'barbershop')}),
        ('Permissões', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
        )}),
        ('Datas importantes', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'tipo_perfil', 'barbershop', 'password1', 'password2'),
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'last_login']
