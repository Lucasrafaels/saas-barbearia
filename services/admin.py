"""
Registro do modelo Service no Django Admin.
"""
from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['nome', 'barbershop', 'preco', 'duracao', 'ativo']
    list_filter = ['barbershop', 'ativo']
    search_fields = ['nome']
