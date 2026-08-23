from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from barbershops.models import Barber, Barbershop
from services.models import Service
from .models import Appointment


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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)
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
        """Editar campos que não sejam `data_hora` (ex.: marcar como
        "realizado") continua permitido mesmo depois que o horário do
        agendamento já passou — senão seria impossível encerrar o fluxo
        normal de um agendamento.

        Testado diretamente no model, e não via API: o
        `AppointmentSerializer.validate()` monta uma cópia solta
        (`Appointment()`) do agendamento para chamar `full_clean()`, e
        essa cópia nunca é marcada como já persistida. Isso faz o
        `validate_unique()` do Django tratar QUALQUER PATCH que chegue a
        essa etapa sem outro erro antes como um "ID já existe" — um bug
        pré-existente no serializer, sem relação com as regras desta
        tarefa (reproduz mesmo antes destas alterações, com um simples
        PATCH de `observacoes` em um agendamento futuro). Fica fora do
        escopo pedido aqui; testar no model isola exatamente a regra
        implementada em `clean()`.
        """
        agendamento = Appointment.objects.create(
            barbershop=self.barbershop,
            cliente=self.client_user,
            barbeiro=self.barber,
            servico=self.service,
            data_hora=self.local_datetime(-1, 10, 0),
        )

        agendamento.status = Appointment.Status.REALIZADO
        agendamento.observacoes = 'Atendimento concluído'
        agendamento.full_clean()  # não deve levantar, mesmo com data_hora no passado
        agendamento.save()

        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Appointment.Status.REALIZADO)
        self.assertEqual(agendamento.observacoes, 'Atendimento concluído')

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