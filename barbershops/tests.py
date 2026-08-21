from datetime import time

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Barber, Barbershop


class BarbershopSecurityTests(APITestCase):
    def setUp(self):
        self.barbershop = self.create_barbershop('Central', 'central@example.com')
        self.other_barbershop = self.create_barbershop('Sul', 'sul@example.com')
        self.admin = self.create_user(
            'admin@example.com', User.TipoPerfil.ADMIN, self.barbershop
        )
        self.client_user = self.create_user(
            'cliente@example.com', User.TipoPerfil.CLIENTE, self.barbershop
        )

    @staticmethod
    def create_barbershop(nome, email):
        return Barbershop.objects.create(
            nome=nome,
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email=email,
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )

    @staticmethod
    def create_user(email, tipo_perfil, barbershop):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=barbershop,
        )

    def test_barber_model_and_api_reject_user_from_another_tenant(self):
        barber_user = self.create_user(
            'barbeiro-outra@example.com',
            User.TipoPerfil.BARBEIRO,
            self.other_barbershop,
        )
        barber = Barber(user=barber_user, barbershop=self.barbershop)

        with self.assertRaises(ValidationError):
            barber.full_clean()

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse('barber-list'),
            {'user': barber_user.pk, 'especialidade': 'Corte'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Barber.objects.filter(user=barber_user).exists())

    def test_only_admin_can_update_the_barbershop(self):
        url = reverse('barbershop-detail', args=[self.barbershop.pk])
        self.client.force_authenticate(self.client_user)

        forbidden_response = self.client.patch(url, {'ativo': False}, format='json')

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
        self.barbershop.refresh_from_db()
        self.assertTrue(self.barbershop.ativo)

        self.client.force_authenticate(self.admin)
        allowed_response = self.client.patch(url, {'ativo': False}, format='json')

        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
        self.barbershop.refresh_from_db()
        self.assertFalse(self.barbershop.ativo)
