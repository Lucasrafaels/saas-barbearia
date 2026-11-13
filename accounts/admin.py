"""
Registro do modelo User no Django Admin.P
"""
from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected as django_delete_selected
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy

from .admin_integrity import AdminIntegrityError, check_admin_removal, check_self_change
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
    # Substitui a ação padrão do site pela versão abaixo, que respeita o BUS-01.
    actions = ['delete_selected']

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

    # BUS-01 — as regras ficam em accounts.admin_integrity e no modelo. Aqui só
    # antecipamos a mensagem para quem usa o Admin e evitamos que uma recusa
    # do modelo apareça como erro 500.

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            return form
        return type(form.__name__, (form,), {'actor': request.user})

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except AdminIntegrityError as error:
            # Só acontece se outra operação mudar os admins entre a validação
            # do formulário e a gravação. A transação do Admin é desfeita.
            raise PermissionDenied(' '.join(error.messages)) from error

    def _deletion_error(self, request, users):
        try:
            for user in users:
                check_self_change(request.user, user, deleting=True)
            check_admin_removal([user.pk for user in users])
        except AdminIntegrityError as error:
            return ' '.join(error.messages)
        return None

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        error = (
            obj is not None
            and self.has_delete_permission(request, obj)
            and self._deletion_error(request, [obj])
        )
        if error:
            self.message_user(request, error, messages.ERROR)
            return HttpResponseRedirect(reverse('admin:accounts_user_change', args=[obj.pk]))
        return super().delete_view(request, object_id, extra_context)

    def delete_model(self, request, obj):
        try:
            super().delete_model(request, obj)
        except AdminIntegrityError as error:
            raise PermissionDenied(' '.join(error.messages)) from error

    @admin.action(permissions=['delete'], description=gettext_lazy('Delete selected %(verbose_name_plural)s'))
    def delete_selected(self, request, queryset):
        error = self._deletion_error(request, list(queryset))
        if error:
            self.message_user(request, error, messages.ERROR)
            return None
        try:
            # A ação padrão grava o histórico (LogEntry) antes de excluir e não
            # usa transação; aqui as duas coisas são desfeitas juntas se o
            # modelo recusar a exclusão.
            with transaction.atomic():
                return django_delete_selected(self, request, queryset)
        except AdminIntegrityError as error:
            self.message_user(request, ' '.join(error.messages), messages.ERROR)
            return None
