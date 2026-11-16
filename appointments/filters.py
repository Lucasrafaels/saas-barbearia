"""
Filtros da listagem de agendamentos (TEN-01, SEC-10).

O ``filterset_fields = ['status', 'barbeiro', 'servico']`` gerava filtros com
``Barber.objects.all()`` e ``Service.objects.all()``. Um ID de outra barbearia
era uma "escolha válida" (200, lista vazia), e um inexistente, não (400): um
oráculo de existência. Aqui as opções vêm da barbearia do usuário autenticado,
e os dois casos recebem a mesma resposta.
"""
import django_filters

from barbershops.models import Barber
from config.tenancy import barbearia_do_pedido, limitar_a_barbearia
from services.models import Service

from .models import Appointment


def barbeiros_do_tenant(request):
    return limitar_a_barbearia(Barber.objects.all(), barbearia_do_pedido(request))


def servicos_do_tenant(request):
    return limitar_a_barbearia(Service.objects.all(), barbearia_do_pedido(request))


class AppointmentFilter(django_filters.FilterSet):
    barbeiro = django_filters.ModelChoiceFilter(queryset=barbeiros_do_tenant)
    servico = django_filters.ModelChoiceFilter(queryset=servicos_do_tenant)

    class Meta:
        model = Appointment
        fields = ['status', 'barbeiro', 'servico']
