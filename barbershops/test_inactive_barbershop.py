"""
BUS-02 — barbearia desativada não continua operando.

Regra: com `Barbershop.ativo=False`, a agenda fica congelada. Ninguém cria,
remarca, confirma ou conclui agendamentos, e a consulta de horários livres
é recusada. Continuam disponíveis o login, a consulta (histórico, agenda,
dados da barbearia, faturamento do admin), o cancelamento de horários já
marcados e a reativação pelo admin. Nada é apagado.
"""
from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from appointments.models import Appointment
from barbershops.models import Barber, Barbershop
from services.models import Service

PASSWORD = 'Senha-segura-123'
DESATIVADA = 'barbearia está desativada'


def local(days, hour, minute=0):
    return timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=days), time(hour, minute)))


class InactiveBarbershopTests(APITestCase):
    def setUp(self):
        self.shop = Barbershop.objects.create(
            nome='Barbearia Central', endereco='Rua Principal, 100', telefone='11999999999',
            email='central@example.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.shop)
        self.service = Service.objects.create(barbershop=self.shop, nome='Corte', preco='50.00', duracao=30)

        # Histórico: um atendimento realizado, um confirmado já encerrado
        # (aguardando ser marcado como realizado) e um horário futuro.
        self.done = self.create_appointment(local(-3, 10), Appointment.Status.REALIZADO)
        self.past_confirmed = self.create_appointment(local(-1, 10), Appointment.Status.CONFIRMADO)
        self.upcoming = self.create_appointment(local(2, 10), Appointment.Status.AGENDADO)

    def create_user(self, email, perfil):
        return User.objects.create_user(
            email=email, nome=email.split('@')[0].title(), password=PASSWORD,
            tipo_perfil=perfil, barbershop=self.shop,
        )

    def create_appointment(self, data_hora, status_):
        return Appointment.objects.create(
            barbershop=self.shop, cliente=self.client_user, barbeiro=self.barber,
            servico=self.service, data_hora=data_hora, status=status_, preco_historico='50.00',
        )

    def deactivate(self):
        Barbershop.objects.filter(pk=self.shop.pk).update(ativo=False)

    def as_user(self, user):
        self.client.force_authenticate(user)

    def book(self, user, data_hora=None):
        return self.client.post(reverse('appointment-list'), {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': (data_hora or local(3, 11)).isoformat(),
        }, format='json')

    def patch(self, appointment, payload):
        return self.client.patch(reverse('appointment-detail', args=[appointment.pk]), payload, format='json')

    def slots(self):
        return self.client.get(reverse('appointment-available-slots'), {
            'barbeiro': self.barber.pk, 'servico': self.service.pk,
            'data': (timezone.localdate() + timedelta(days=3)).isoformat(),
        })

    def assert_blocked(self, response):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(DESATIVADA, str(response.data))

    # Barbearia ativa realizando operações normalmente ------------------------

    def test_barbearia_ativa_opera_normalmente(self):
        self.as_user(self.client_user)
        self.assertEqual(self.slots().status_code, status.HTTP_200_OK)
        created = self.book(self.client_user)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

        self.as_user(self.barber.user)
        self.assertEqual(self.patch(self.upcoming, {'status': 'confirmado'}).status_code, status.HTTP_200_OK)
        self.assertEqual(self.patch(self.past_confirmed, {'status': 'realizado'}).status_code, status.HTTP_200_OK)

    # Barbearia desativada tentando criar agendamentos ------------------------

    def test_nenhum_perfil_cria_agendamento_em_barbearia_desativada(self):
        self.deactivate()
        before = Appointment.objects.count()

        for user in (self.client_user, self.barber.user, self.admin):
            self.as_user(user)
            self.assert_blocked(self.book(user))

        self.assertEqual(Appointment.objects.count(), before)

    def test_regra_vale_fora_da_api(self):
        """Defesa no modelo: Django Admin e scripts também passam por clean()."""
        self.deactivate()
        appointment = Appointment(
            barbershop=self.shop, cliente=self.client_user, barbeiro=self.barber,
            servico=self.service, data_hora=local(3, 11),
        )

        with self.assertRaises(ValidationError) as ctx:
            appointment.full_clean()
        self.assertIn('barbershop', ctx.exception.message_dict)

    # Cliente em barbearia desativada ----------------------------------------

    def test_cliente_nao_consulta_horarios_nem_remarca(self):
        self.deactivate()
        self.as_user(self.client_user)

        response = self.slots()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(DESATIVADA, response.data['detail'])

        self.assert_blocked(self.patch(self.upcoming, {'data_hora': local(3, 14).isoformat()}))
        self.upcoming.refresh_from_db()
        self.assertEqual(self.upcoming.data_hora, local(2, 10))

    def test_cliente_ainda_consulta_historico_e_cancela_horario_marcado(self):
        self.deactivate()
        self.as_user(self.client_user)

        listing = self.client.get(reverse('appointment-list'))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data['count'], 3)

        response = self.patch(self.upcoming, {'status': 'cancelado'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.upcoming.refresh_from_db()
        self.assertEqual(self.upcoming.status, Appointment.Status.CANCELADO)

    # Barbeiro em barbearia desativada ----------------------------------------

    def test_barbeiro_nao_confirma_conclui_nem_remarca(self):
        self.deactivate()
        self.as_user(self.barber.user)

        self.assert_blocked(self.patch(self.upcoming, {'status': 'confirmado'}))
        self.assert_blocked(self.patch(self.past_confirmed, {'status': 'realizado'}))
        self.assert_blocked(self.patch(self.upcoming, {'data_hora': local(3, 14).isoformat()}))
        self.assertEqual(self.slots().status_code, status.HTTP_400_BAD_REQUEST)

        self.upcoming.refresh_from_db()
        self.past_confirmed.refresh_from_db()
        self.assertEqual(self.upcoming.status, Appointment.Status.AGENDADO)
        self.assertEqual(self.past_confirmed.status, Appointment.Status.CONFIRMADO)

    def test_barbeiro_ainda_consulta_a_propria_agenda(self):
        self.deactivate()
        self.as_user(self.barber.user)

        response = self.client.get(reverse('appointment-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    # Administrador acessando e reativando ------------------------------------

    def test_admin_consulta_a_barbearia_desativada(self):
        self.deactivate()
        self.as_user(self.admin)

        shop = self.client.get(reverse('barbershop-detail', args=[self.shop.pk]))
        self.assertEqual(shop.status_code, status.HTTP_200_OK)
        self.assertFalse(shop.data['ativo'])

        for name in ('appointment-list', 'user-list', 'service-list', 'barber-list'):
            self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_200_OK, name)

        report = self.client.get(reverse('appointment-revenue-report'), {
            'start': (timezone.localdate() - timedelta(days=7)).isoformat(),
        })
        self.assertEqual(report.status_code, status.HTTP_200_OK)
        self.assertEqual(report.data['total_appointments'], 1)

        # Também não opera a agenda enquanto a barbearia está desativada.
        self.assert_blocked(self.patch(self.upcoming, {'status': 'confirmado'}))
        # Mas pode cancelar um horário que não vai acontecer.
        self.assertEqual(
            self.client.delete(reverse('appointment-detail', args=[self.upcoming.pk])).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_admin_desativa_e_reativa_a_barbearia(self):
        self.as_user(self.admin)
        url = reverse('barbershop-detail', args=[self.shop.pk])

        response = self.client.patch(url, {'ativo': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.as_user(self.client_user)
        self.assert_blocked(self.book(self.client_user))

        self.as_user(self.admin)
        response = self.client.patch(url, {'ativo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ativo'])

        self.as_user(self.client_user)
        created = self.book(self.client_user)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

    # Preservação dos registros históricos ------------------------------------

    def snapshot(self):
        return {
            'appointments': list(Appointment.objects.order_by('pk').values_list('pk', 'status', 'data_hora', 'preco_historico')),
            'users': list(User.objects.order_by('pk').values_list('pk', 'tipo_perfil', 'is_active')),
            'barbers': list(Barber.objects.order_by('pk').values_list('pk', 'ativo')),
            'services': list(Service.objects.order_by('pk').values_list('pk', 'ativo')),
        }

    def test_desativacao_preserva_os_registros(self):
        before = self.snapshot()

        self.as_user(self.admin)
        self.client.patch(reverse('barbershop-detail', args=[self.shop.pk]), {'ativo': False}, format='json')
        self.assertEqual(self.snapshot(), before)

        # A desativação pela plataforma (DELETE com confirmação) também só marca ativo=False.
        Barbershop.objects.filter(pk=self.shop.pk).update(ativo=True)
        staff = User.objects.create_superuser(email='plataforma@example.com', nome='Plataforma', password=PASSWORD)
        before = self.snapshot()
        self.as_user(staff)
        response = self.client.delete(
            reverse('barbershop-detail', args=[self.shop.pk]) + '?' + urlencode({'confirmar': self.shop.nome})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.ativo)
        self.assertEqual(self.snapshot(), before)


class OtherBarbershopUnaffectedTests(APITestCase):
    def test_desativar_uma_barbearia_nao_afeta_outra(self):
        shops = [
            Barbershop.objects.create(
                nome=f'Barbearia {n}', endereco='Rua', telefone='11999999999', email=f'{n}@example.com',
                horario_abertura=time(8), horario_fechamento=time(18), ativo=(n == 'ativa'),
            )
            for n in ('inativa', 'ativa')
        ]
        active = shops[1]
        client_user = User.objects.create_user(
            email='c@example.com', nome='C', password=PASSWORD,
            tipo_perfil=User.TipoPerfil.CLIENTE, barbershop=active,
        )
        barber = Barber.objects.create(
            user=User.objects.create_user(
                email='b@example.com', nome='B', password=PASSWORD,
                tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=active,
            ),
            barbershop=active,
        )
        service = Service.objects.create(barbershop=active, nome='Corte', preco='50.00', duracao=30)
        self.client.force_authenticate(client_user)

        response = self.client.post(reverse('appointment-list'), {
            'cliente': client_user.pk, 'barbeiro': barber.pk, 'servico': service.pk,
            'data_hora': local(3, 11).isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
