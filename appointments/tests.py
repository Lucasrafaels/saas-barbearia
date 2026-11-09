import threading
from datetime import datetime, time, timedelta
from unittest import mock, skipUnless

from django.core.exceptions import ValidationError
from django.db import connection, close_old_connections
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.test import TransactionTestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentSecurityTests(APITestCase):
    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.client_user = self.create_user(
            'cliente@example.com', User.TipoPerfil.CLIENTE
        )
        self.other_client = self.create_user(
            'outro-cliente@example.com', User.TipoPerfil.CLIENTE
        )
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN)
        barber_user = self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte',
            preco='50.00',
            duracao=30,
        )
        self.start = (timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0)
        self.existing_appointment = self.create_appointment(self.start)
        self.client.force_authenticate(self.client_user)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def create_appointment(self, data_hora):
        return Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=data_hora,
        )

    def appointment_payload(self, data_hora):
        return {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': data_hora.isoformat(),
        }

    def test_api_rejects_overlapping_appointments_on_create_and_update(self):
        create_response = self.client.post(
            reverse('appointment-list'),
            self.appointment_payload(self.start + timedelta(minutes=15)),
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', create_response.data)

        later_appointment = self.create_appointment(self.start + timedelta(minutes=60))
        update_response = self.client.patch(
            reverse('appointment-detail', args=[later_appointment.pk]),
            {'data_hora': (self.start + timedelta(minutes=15)).isoformat()},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', update_response.data)
        later_appointment.refresh_from_db()
        self.assertEqual(later_appointment.data_hora, self.start + timedelta(minutes=60))

    def test_client_cannot_transfer_own_appointment(self):
        response = self.client.patch(
            reverse('appointment-detail', args=[self.existing_appointment.pk]),
            {'cliente': self.other_client.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.existing_appointment.refresh_from_db()
        self.assertEqual(self.existing_appointment.cliente_id, self.client_user.pk)

    def test_appointment_cliente_must_have_client_role(self):
        self.client.force_authenticate(self.admin)
        payload = self.appointment_payload(self.start + timedelta(minutes=60))
        payload['cliente'] = self.admin.pk

        response = self.client.post(reverse('appointment-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)

    def test_barber_sees_and_manages_only_own_appointments(self):
        other_barber_user = self.create_user(
            'outro-barbeiro@example.com', User.TipoPerfil.BARBEIRO
        )
        other_barber = Barber.objects.create(
            user=other_barber_user,
            barbershop=self.barbershop,
        )
        other_appointment = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=other_barber,
            servico=self.service,
            data_hora=self.start + timedelta(minutes=60),
        )
        self.client.force_authenticate(self.barber.user)

        list_response = self.client.get(reverse('appointment-list'))
        blocked_response = self.client.patch(
            reverse('appointment-detail', args=[other_appointment.pk]),
            {'observacoes': 'Alteração indevida'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in list_response.data['results']],
            [self.existing_appointment.pk],
        )
        self.assertEqual(blocked_response.status_code, status.HTTP_404_NOT_FOUND)

        create_response = self.client.post(
            reverse('appointment-list'),
            {
                **self.appointment_payload(self.start + timedelta(minutes=60)),
                'barbeiro': other_barber.pk,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('barbeiro', create_response.data)


class AppointmentBusinessHoursAndPastDateTests(APITestCase):
    """
    Cobre as duas regras novas de `Appointment.clean()`:

    1) o agendamento — do início ao fim, considerando a duração do
       serviço — precisa caber dentro do horário de funcionamento da
       barbearia (horario_abertura / horario_fechamento);
    2) não é permitido marcar nem remarcar um agendamento para uma
       data/hora que já passou — mas editar outros campos de um
       agendamento cuja data já passou (ex.: marcar como "realizado")
       continua permitido.

    A barbearia de fixture funciona das 8h às 18h e o serviço dura 30
    minutos. Os horários usados nos testes são construídos no fuso
    horário local do projeto (settings.TIME_ZONE), para bater com a
    forma como o model compara `data_hora` com `horario_abertura` /
    `horario_fechamento`.

    Nota: um teste desta classe (test_can_update_other_fields_on_a_past_appointment)
    valida a regra diretamente no model em vez de via API, por causa de
    um bug pré-existente e não relacionado no `AppointmentSerializer`
    (ver docstring do próprio teste).
    """

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura=time(8, 0),
            horario_fechamento=time(18, 0),
        )
        self.admin = self.create_user('admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte',
            preco='50.00',
            duracao=30,
        )
        self.client.force_authenticate(self.admin)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    @staticmethod
    def local_datetime(dias_a_partir_de_hoje, hora, minuto=0):
        """Monta um datetime ciente de fuso horário, no horário local do
        projeto, para o dia `hoje + dias_a_partir_de_hoje` no horário
        informado."""
        dia = timezone.localdate() + timedelta(days=dias_a_partir_de_hoje)
        return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))

    def appointment_payload(self, data_hora, **overrides):
        payload = {
            'cliente': self.client_user.pk,
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data_hora': data_hora.isoformat(),
        }
        payload.update(overrides)
        return payload

    # ------------------------------------------------------------------
    # Horário de funcionamento
    # ------------------------------------------------------------------
    def test_rejects_appointment_starting_before_opening(self):
        data_hora = self.local_datetime(1, 7, 30)  # abre às 8h

        response = self.client.post(
            reverse('appointment-list'), self.appointment_payload(data_hora), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
        self.assertFalse(Appointment.objects.filter(data_hora=data_hora).exists())

    def test_rejects_appointment_ending_after_closing(self):
        # serviço de 30 min às 17:45 terminaria 18:15, depois do fechamento (18h)
        data_hora = self.local_datetime(1, 17, 45)

        response = self.client.post(
            reverse('appointment-list'), self.appointment_payload(data_hora), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
        self.assertFalse(Appointment.objects.filter(data_hora=data_hora).exists())

    def test_accepts_appointment_exactly_at_business_hours_boundaries(self):
        inicio_no_limite_abertura = self.local_datetime(1, 8, 0)
        response = self.client.post(
            reverse('appointment-list'),
            self.appointment_payload(inicio_no_limite_abertura),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # serviço de 30 min às 17:30 termina exatamente às 18:00 (fechamento)
        termina_no_limite_fechamento = self.local_datetime(1, 17, 30)
        response2 = self.client.post(
            reverse('appointment-list'),
            self.appointment_payload(termina_no_limite_fechamento),
            format='json',
        )
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

    def test_appointment_outside_business_hours_rejected_at_model_level(self):
        appointment = Appointment(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(1, 6, 0),
        )

        with self.assertRaises(ValidationError):
            appointment.clean()

    def test_rejects_update_that_moves_appointment_outside_business_hours(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(1, 10, 0),
        )
        fora_do_horario = self.local_datetime(1, 19, 0)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'data_hora': fora_do_horario.isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
        agendamento.refresh_from_db()
        self.assertNotEqual(agendamento.data_hora, fora_do_horario)

    # ------------------------------------------------------------------
    # Não permite agendamento no passado
    # ------------------------------------------------------------------
    def test_rejects_appointment_in_the_past_on_create(self):
        data_hora = self.local_datetime(-1, 10, 0)  # ontem, dentro do horário

        response = self.client.post(
            reverse('appointment-list'), self.appointment_payload(data_hora), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
        self.assertFalse(Appointment.objects.filter(data_hora=data_hora).exists())

    def test_rejects_rescheduling_appointment_to_the_past(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(1, 10, 0),
        )
        data_hora_passada = self.local_datetime(-1, 10, 0)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'data_hora': data_hora_passada.isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
        agendamento.refresh_from_db()
        self.assertNotEqual(agendamento.data_hora, data_hora_passada)

    def test_can_update_other_fields_on_a_past_appointment(self):
        """Editar campos que não sejam `data_hora` (ex.: status/observacoes)
        segue a máquina de estados mesmo depois que o horário passou.
        O fluxo correto é: agendado → confirmado → realizado.
        """
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-1, 10, 0),
        )

        # Primeiro: agendado → confirmado
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.CONFIRMADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CONFIRMADO)

        # Segundo: confirmado → realizado (com observações)
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'status': Appointment.Status.REALIZADO,
                'observacoes': 'Atendimento concluído',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.REALIZADO)
        self.assertEqual(agendamento.observacoes, 'Atendimento concluído')

        # Tentativa direta agendado → realizado deve falhar
        agendamento2 = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-2, 10, 0),
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento2.pk]),
            {'status': Appointment.Status.REALIZADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_appointment_in_the_past_rejected_at_model_level(self):
        appointment = Appointment(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-1, 10, 0),
        )

        with self.assertRaises(ValidationError):
            appointment.clean()

class AvailableSlotsTests(APITestCase):
    """
    Testes do endpoint GET /api/v1/appointments/available-slots/.
    """
    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Slots',
            endereco='Rua dos Horários, 10',
            telefone='11988888888',
            email='slots@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(12),
        )
        self.admin = self.create_user('slots-admin@example.com', User.TipoPerfil.ADMIN)
        barber_user = self.create_user('slots-barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte Slots',
            preco='40.00',
            duracao=60,
        )
        self.client.force_authenticate(self.admin)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def url(self, **params):
        return reverse('appointment-available-slots')

    def local_datetime(self, day_offset, hour, minute=0):
        naive = datetime.now() + timedelta(days=day_offset)
        data = (naive.replace(hour=hour, minute=minute, second=0, microsecond=0)).date()
        return timezone.make_aware(datetime.combine(data, time(hour, minute)))

    def data_str(self, day_offset):
        return (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d')

    def test_slots_livres_gerados_com_passo_da_duracao(self):
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Abertura 08:00, fechamento 12:00 e duração de 60 min:
        # últimos slot válido começa às 11:00.
        self.assertEqual(
            response.data['slots'],
            ['08:00', '09:00', '10:00', '11:00'],
        )

    def test_slot_conflitante_eh_removido(self):
        Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.admin,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slots'], ['08:00', '10:00', '11:00'])

    def test_agendamento_cancelado_nao_bloqueia_slot(self):
        Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.admin,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
            status=Appointment.Status.CANCELADO,
        )
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slots'], ['08:00', '09:00', '10:00', '11:00'])

    def test_agendamento_de_outro_barbeiro_nao_bloqueia(self):
        outro_user = self.create_user('outro-barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        outro_barber = Barber.objects.create(user=outro_user, barbershop=self.barbershop)
        Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.admin,
            barbeiro=outro_barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slots'], ['08:00', '09:00', '10:00', '11:00'])

    def test_parametros_ausentes_retornam_400(self):
        response = self.client.get(self.url(), {'data': self.data_str(2)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_data_invalida_retorna_400(self):
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': '25/08/2026',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_barbeiro_inexistente_retorna_404(self):
        response = self.client.get(self.url(), {
            'barbeiro': 99999,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_recurso_de_outro_tenant_retorna_404_sem_revelar_existencia(self):
        outra = Barbershop.objects.create(
            nome='Outra Barbearia', endereco='Rua B, 2', telefone='11900000000',
            email='outra@example.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        outro_usuario = User.objects.create_user(
            email='outro-slots@example.com', nome='Outro', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=outra,
        )
        outro_barbeiro = Barber.objects.create(user=outro_usuario, barbershop=outra)
        response = self.client.get(self.url(), {
            'barbeiro': outro_barbeiro.pk,
            'servico': self.service.pk,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_recurso_inativo_nao_oferece_horarios(self):
        self.barber.ativo = False
        self.barber.save(update_fields=['ativo'])
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.pk,
            'servico': self.service.pk,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requer_autenticacao(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AppointmentPermissionTests(APITestCase):
    """Garante que clientes não alterem status e DELETE preserve histórico."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Permissões',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='permissoes@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.client_user = User.objects.create_user(
            email='cliente-permissoes@example.com', nome='Cliente',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        barber_user = User.objects.create_user(
            email='barbeiro-permissoes@example.com', nome='Barbeiro',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop, nome='Corte', preco='50.00', duracao=30,
        )
        self.appointment = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=timezone.now() + timedelta(days=1),
        )

    def test_client_cannot_change_appointment_status(self):
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[self.appointment.pk]),
            {'status': Appointment.Status.REALIZADO},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.AGENDADO)

    def test_delete_cancels_instead_of_removing_appointment(self):
        self.client.force_authenticate(self.client_user)

        response = self.client.delete(
            reverse('appointment-detail', args=[self.appointment.pk]),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Appointment.objects.filter(pk=self.appointment.pk).exists())
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELADO)


@skipUnless(connection.vendor == 'postgresql', 'Requer bloqueio real do PostgreSQL.')
class AppointmentConcurrencyTests(TransactionTestCase):
    """Duas requisições simultâneas não podem reservar o mesmo horário."""

    reset_sequences = True

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Concorrência',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='concorrencia@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.client_user = User.objects.create_user(
            email='cliente-concorrencia@example.com', nome='Cliente',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        barber_user = User.objects.create_user(
            email='barbeiro-concorrencia@example.com', nome='Barbeiro',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop, nome='Corte', preco='50.00', duracao=30,
        )
        self.data_hora = timezone.make_aware(
            datetime.combine(timezone.localdate() + timedelta(days=1), time(10)),
        )

    def test_concurrent_requests_create_only_one_appointment(self):
        barrier = threading.Barrier(2)
        outcomes = []
        failures = []
        original_validate = AppointmentSerializer.validate

        def synchronize_after_initial_validation(serializer, attrs):
            result = original_validate(serializer, attrs)
            barrier.wait(timeout=10)
            return result

        def create_appointment():
            close_old_connections()
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=self.client_user.pk))
            try:
                response = client.post(
                    reverse('appointment-list'),
                    {
                        'cliente': self.client_user.pk,
                        'barbeiro': self.barber.pk,
                        'servico': self.service.pk,
                        'data_hora': self.data_hora.isoformat(),
                    },
                    format='json',
                )
                outcomes.append(response.status_code)
            except Exception as error:  # pragma: no cover - repropagado abaixo
                failures.append(error)
            finally:
                close_old_connections()

        with mock.patch.object(AppointmentSerializer, 'validate', synchronize_after_initial_validation):
            workers = [threading.Thread(target=create_appointment) for _ in range(2)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=15)

        self.assertFalse(failures, failures)
        self.assertEqual(sorted(outcomes), [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
        self.assertEqual(Appointment.objects.count(), 1)


class AvailableSlotsExcludeAppointmentTests(APITestCase):
    """Testes para o parâmetro exclude_appointment_id no endpoint available-slots."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Exclude',
            endereco='Rua dos Excluídos, 10',
            telefone='11977777777',
            email='exclude@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(12),
        )
        self.admin = self.create_user('exclude-admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente-exclude@example.com', User.TipoPerfil.CLIENTE)
        self.other_client = self.create_user('other-client@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro-exclude@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte Exclude',
            preco='40.00',
            duracao=60,
        )
        self.client.force_authenticate(self.admin)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def url(self):
        return reverse('appointment-available-slots')

    def local_datetime(self, day_offset, hour, minute=0):
        naive = datetime.now() + timedelta(days=day_offset)
        data = (naive.replace(hour=hour, minute=minute, second=0, microsecond=0)).date()
        return timezone.make_aware(datetime.combine(data, time(hour, minute)))

    def data_str(self, day_offset):
        return (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d')

    def test_exclude_own_appointment_from_slots(self):
        """Ao reagendar, o próprio agendamento não deve bloquear o slot original."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )

        # Sem exclude: o slot 09:00 está ocupado
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('09:00', response.data['slots'])

        # Com exclude: o slot 09:00 deve aparecer livre
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('09:00', response.data['slots'])

    def test_exclude_appointment_not_found(self):
        """Agendamento inexistente retorna 404."""
        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': 99999,
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_exclude_appointment_wrong_tenant(self):
        """Agendamento de outro tenant não pode ser usado no exclude."""
        outra = Barbershop.objects.create(
            nome='Outra', endereco='Rua B', telefone='11900000000',
            email='outra@ex.com', horario_abertura=time(8), horario_fechamento=time(18),
        )
        outro_usuario = User.objects.create_user(
            email='outro@example.com', nome='Outro', password='Senha-segura-123',
            tipo_perfil=User.TipoPerfil.BARBEIRO, barbershop=outra,
        )
        outro_barbeiro = Barber.objects.create(user=outro_usuario, barbershop=outra)
        outro_servico = Service.objects.create(
            barbershop=outra, nome='Corte', preco='50.00', duracao=30,
        )
        outro_agendamento = Appointment.objects.create(
            barbershop=outra,
            cliente=self.admin,  # usando admin só para criar
            barbeiro=outro_barbeiro,
            servico=outro_servico,
            data_hora=self.local_datetime(2, 9, 0),
        )

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': outro_agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_exclude_appointment_client_no_permission(self):
        """Cliente não pode excluir agendamento de outro cliente."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.other_client,  # pertence a outro cliente
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_exclude_appointment_barber_no_permission(self):
        """Barbeiro não pode excluir agendamento de outro barbeiro."""
        outro_barbeiro_user = self.create_user('outro-barbeiro@example.com', User.TipoPerfil.BARBEIRO)
        outro_barbeiro = Barber.objects.create(user=outro_barbeiro_user, barbershop=self.barbershop)
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=outro_barbeiro,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )
        barbeiro_user = User.objects.get(email='barbeiro-exclude@example.com')
        self.client.force_authenticate(barbeiro_user)

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_exclude_appointment_wrong_barber(self):
        """exclude_appointment_id de outro barbeiro é ignorado (não bloqueia slots)."""
        outro_barbeiro_user = self.create_user('outro-barbeiro2@example.com', User.TipoPerfil.BARBEIRO)
        outro_barbeiro = Barber.objects.create(user=outro_barbeiro_user, barbershop=self.barbershop)
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=outro_barbeiro,  # barbeiro diferente
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
        )

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,  # barbeiro da consulta diferente do agendamento
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        # Deve retornar 200 e ignorar o agendamento de outro barbeiro
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # O agendamento original não estava no barbeiro consultado, então não afeta os slots
        self.assertIn('slots', response.data)

    def test_exclude_appointment_status_not_reschedulable(self):
        """Não permite excluir agendamento com status realizado."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
            status=Appointment.Status.REALIZADO,
        )

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('realizado', response.data['detail'].lower())

    def test_exclude_appointment_cancelado(self):
        """Não permite excluir agendamento cancelado."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 9, 0),
            status=Appointment.Status.CANCELADO,
        )

        response = self.client.get(self.url(), {
            'barbeiro': self.barber.id,
            'servico': self.service.id,
            'data': self.data_str(2),
            'exclude_appointment_id': agendamento.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cancelado', response.data['detail'].lower())


class AppointmentReschedulingTests(APITestCase):
    """Testes de reagendamento completo."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Reagend',
            endereco='Rua Reagend, 10',
            telefone='11966666666',
            email='reagend@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = self.create_user('reagend-admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente-reagend@example.com', User.TipoPerfil.CLIENTE)
        self.other_client = self.create_user('other-client-reagend@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro-reagend@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.other_barber_user = self.create_user('outro-barbeiro-reagend@example.com', User.TipoPerfil.BARBEIRO)
        self.other_barber = Barber.objects.create(user=self.other_barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte Reagend',
            preco='40.00',
            duracao=60,
        )
        self.other_service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Barba',
            preco='30.00',
            duracao=30,
        )

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def local_datetime(self, day_offset, hour, minute=0):
        naive = datetime.now() + timedelta(days=day_offset)
        data = (naive.replace(hour=hour, minute=minute, second=0, microsecond=0)).date()
        return timezone.make_aware(datetime.combine(data, time(hour, minute)))

    def test_reschedule_same_time_allowed(self):
        """Reagendar para o mesmo horário deve ser permitido (idempotente)."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': agendamento.data_hora.isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.AGENDADO)

    def test_reschedule_to_available_time(self):
        """Reagendar para outro horário disponível."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        nova_data_hora = self.local_datetime(2, 11, 0)
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': nova_data_hora.isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.data_hora, nova_data_hora)

    def test_reschedule_conflict_rejected(self):
        """Reagendar para horário ocupado deve ser rejeitado."""
        Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.other_client,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 11, 0),
        )
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': self.local_datetime(2, 11, 0).isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('já possui um agendamento neste horário', str(response.data).lower())

    def test_reschedule_cancelled_rejected(self):
        """Não pode reagendar agendamento cancelado."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CANCELADO,
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': self.local_datetime(2, 11, 0).isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reschedule_completed_rejected(self):
        """Não pode reagendar agendamento realizado."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.REALIZADO,
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': self.local_datetime(2, 11, 0).isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reschedule_other_client_rejected(self):
        """Cliente não pode reagendar agendamento de outro cliente."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.other_client,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': self.local_datetime(2, 11, 0).isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reschedule_to_past_rejected(self):
        """Não pode reagendar para horário no passado."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {
                'data_hora': self.local_datetime(-1, 10, 0).isoformat(),
                'barbeiro': self.barber.id,
                'servico': self.service.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AppointmentCancelByDeleteTests(APITestCase):
    """Testes de cancelamento via DELETE."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Delete',
            endereco='Rua Delete, 10',
            telefone='11955555555',
            email='delete@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = self.create_user('delete-admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente-delete@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro-delete@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte Delete',
            preco='40.00',
            duracao=60,
        )

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def local_datetime(self, day_offset, hour, minute=0):
        naive = datetime.now() + timedelta(days=day_offset)
        data = (naive.replace(hour=hour, minute=minute, second=0, microsecond=0)).date()
        return timezone.make_aware(datetime.combine(data, time(hour, minute)))

    def test_cancel_scheduled_by_delete(self):
        """DELETE cancela agendamento 'agendado'."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.delete(reverse('appointment-detail', args=[agendamento.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)

    def test_cancel_confirmed_by_delete(self):
        """DELETE cancela agendamento 'confirmado'."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CONFIRMADO,
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.delete(reverse('appointment-detail', args=[agendamento.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)

    def test_cancel_completed_rejected(self):
        """DELETE não cancela agendamento 'realizado'."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-1, 10, 0),
            status=Appointment.Status.REALIZADO,
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.delete(reverse('appointment-detail', args=[agendamento.pk]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.REALIZADO)

    def test_cancel_already_cancelled_idempotent(self):
        """DELETE em agendamento já cancelado é idempotente (retorna 204)."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CANCELADO,
        )
        self.client.force_authenticate(self.client_user)

        response = self.client.delete(reverse('appointment-detail', args=[agendamento.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)


class AppointmentStateMachineTests(APITestCase):
    """Testes da máquina de estados de status."""

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia State',
            endereco='Rua State, 10',
            telefone='11944444444',
            email='state@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.admin = self.create_user('state-admin@example.com', User.TipoPerfil.ADMIN)
        self.client_user = self.create_user('cliente-state@example.com', User.TipoPerfil.CLIENTE)
        barber_user = self.create_user('barbeiro-state@example.com', User.TipoPerfil.BARBEIRO)
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop,
            nome='Corte State',
            preco='40.00',
            duracao=60,
        )
        self.client.force_authenticate(self.admin)

    def create_user(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def local_datetime(self, day_offset, hour, minute=0):
        naive = datetime.now() + timedelta(days=day_offset)
        data = (naive.replace(hour=hour, minute=minute, second=0, microsecond=0)).date()
        return timezone.make_aware(datetime.combine(data, time(hour, minute)))

    def test_agendado_to_confirmado_allowed(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.CONFIRMADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CONFIRMADO)

    def test_agendado_to_cancelado_allowed(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.CANCELADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)

    def test_agendado_to_realizado_rejected(self):
        """agendado → realizado diretamente NÃO é permitido."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.REALIZADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirmado_to_realizado_allowed(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CONFIRMADO,
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.REALIZADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.REALIZADO)

    def test_confirmado_to_cancelado_allowed(self):
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CONFIRMADO,
        )
        response = self.client.patch(
            reverse('appointment-detail', args=[agendamento.pk]),
            {'status': Appointment.Status.CANCELADO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)

    def test_realizado_no_transitions(self):
        """realizado é estado final - nenhuma transição permitida."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-1, 10, 0),
            status=Appointment.Status.REALIZADO,
        )
        for novo_status in [Appointment.Status.AGENDADO, Appointment.Status.CONFIRMADO, Appointment.Status.CANCELADO]:
            response = self.client.patch(
                reverse('appointment-detail', args=[agendamento.pk]),
                {'status': novo_status},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            agendamento.refresh_from_db()
            self.assertEqual(agendamento.status, Appointment.Status.REALIZADO)

    def test_cancelado_no_transitions(self):
        """cancelado é estado final - nenhuma transição permitida."""
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(2, 10, 0),
            status=Appointment.Status.CANCELADO,
        )
        for novo_status in [Appointment.Status.AGENDADO, Appointment.Status.CONFIRMADO, Appointment.Status.REALIZADO]:
            response = self.client.patch(
                reverse('appointment-detail', args=[agendamento.pk]),
                {'status': novo_status},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            agendamento.refresh_from_db()
            self.assertEqual(agendamento.status, Appointment.Status.CANCELADO)


@skipUnless(connection.vendor == 'postgresql', 'Requer bloqueio real do PostgreSQL.')
class AppointmentConcurrencySlotsTests(TransactionTestCase):
    """Testes de concorrência de horários (slot ocupado)."""

    reset_sequences = True

    def setUp(self):
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Concorrência Slots',
            endereco='Rua Concorrência, 10',
            telefone='11933333333',
            email='concorrencia-slots@example.com',
            horario_abertura=time(8),
            horario_fechamento=time(18),
        )
        self.client_user = User.objects.create_user(
            email='cliente-concorrencia-slots@example.com', nome='Cliente',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        self.other_client = User.objects.create_user(
            email='other-cliente-concorrencia-slots@example.com', nome='Other',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        barber_user = User.objects.create_user(
            email='barbeiro-concorrencia-slots@example.com', nome='Barbeiro',
            password='Senha-segura-123', tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )
        self.barber = Barber.objects.create(user=barber_user, barbershop=self.barbershop)
        self.service = Service.objects.create(
            barbershop=self.barbershop, nome='Corte', preco='50.00', duracao=30,
        )
        self.data_hora = timezone.make_aware(
            datetime.combine(timezone.localdate() + timedelta(days=1), time(10)),
        )

    def test_concurrent_reschedule_to_same_slot_rejected(self):
        """Duas requisições simultâneas de reagendamento para o mesmo slot."""
        agendamento1 = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), time(9))),
        )
        agendamento2 = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.other_client,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), time(11))),
        )

        barrier = threading.Barrier(2)
        outcomes = []
        failures = []

        def reschedule_appointment(appt_id, user):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(user)
            try:
                response = client.patch(
                    reverse('appointment-detail', args=[appt_id]),
                    {
                        'data_hora': self.data_hora.isoformat(),
                        'barbeiro': self.barber.id,
                        'servico': self.service.id,
                    },
                    format='json',
                )
                outcomes.append(response.status_code)
            except Exception as error:
                failures.append(error)
            finally:
                close_old_connections()

        # Tentar reagendar ambos para o mesmo horário (10:00)
        with mock.patch.object(AppointmentSerializer, 'validate', lambda s, a: (barrier.wait(timeout=10), a)[1]):
            workers = [
                threading.Thread(target=reschedule_appointment, args=(agendamento1.pk, self.client_user)),
                threading.Thread(target=reschedule_appointment, args=(agendamento2.pk, self.other_client)),
            ]
            for w in workers:
                w.start()
            for w in workers:
                w.join(timeout=15)

        self.assertFalse(failures, failures)
        # Apenas um deve conseguir
        self.assertEqual(sorted(outcomes), [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        # Verificar que só um está no horário 10:00
        count_10 = Appointment.objects.filter(data_hora=self.data_hora).exclude(status=Appointment.Status.CANCELADO).count()
        self.assertEqual(count_10, 1)
