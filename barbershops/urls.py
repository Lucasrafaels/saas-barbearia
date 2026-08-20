"""
Rotas do app barbershops.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BarberViewSet, BarbershopViewSet

router = DefaultRouter()
router.register('barbershops', BarbershopViewSet, basename='barbershop')
router.register('barbers', BarberViewSet, basename='barber')

urlpatterns = [
    path('', include(router.urls)),
]
