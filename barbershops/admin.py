"""
Registro dos modelos do app barbershops no Django Admin.
"""
from django.contrib import admin

from .models import Barber, Barbershop


@admin.register(Barbershop)
class BarbershopAdmin(admin.ModelAdmin):
    list_display = ['nome', 'telefone', 'email', 'horario_abertura', 'horario_fechamento', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'email', 'telefone']


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ['user', 'barbershop', 'especialidade', 'ativo']
    list_filter = ['barbershop', 'ativo']
    search_fields = ['user__nome', 'user__email', 'especialidade']
    autocomplete_fields = ['user', 'barbershop']
