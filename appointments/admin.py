"""
Registro do modelo Appointment no Django Admin.
"""
from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'barbeiro', 'servico', 'data_hora', 'status', 'barbershop']
    list_filter = ['status', 'barbershop', 'data_hora']
    search_fields = ['cliente__nome', 'barbeiro__user__nome']
    date_hierarchy = 'data_hora'
    autocomplete_fields = ['cliente', 'barbeiro', 'servico']
