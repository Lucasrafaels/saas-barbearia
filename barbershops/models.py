"""
Modelos relacionados à barbearia em si (o "tenant" do sistema) e aos
barbeiros vinculados a ela.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from config.models import TimeStampedModel

# Dias da semana no padrão ISO 8601 (date.isoweekday()): 1 = segunda-feira,
# 7 = domingo. O mesmo número é usado pela API e pelo frontend.
DIAS_DA_SEMANA = {
    1: 'segunda-feira',
    2: 'terça-feira',
    3: 'quarta-feira',
    4: 'quinta-feira',
    5: 'sexta-feira',
    6: 'sábado',
    7: 'domingo',
}
# Forma usada nas mensagens: "A barbearia não abre aos domingos."
DIAS_DA_SEMANA_NO_PLURAL = {
    1: 'às segundas-feiras',
    2: 'às terças-feiras',
    3: 'às quartas-feiras',
    4: 'às quintas-feiras',
    5: 'às sextas-feiras',
    6: 'aos sábados',
    7: 'aos domingos',
}

HORARIO_INVALIDO_MENSAGEM = (
    'O horário de fechamento precisa ser depois do horário de abertura. '
    'A agenda não atravessa a meia-noite: abertura e fechamento são do mesmo dia.'
)


def todos_os_dias():
    """Padrão de `dias_funcionamento`: mantém o comportamento anterior (todos os dias)."""
    return list(DIAS_DA_SEMANA)


def validar_dias_funcionamento(valor):
    """Normaliza e valida a lista de dias (ISO 1..7). Devolve a lista ordenada, sem repetição."""
    if not isinstance(valor, (list, tuple)):
        raise ValidationError('Informe os dias de funcionamento como uma lista de 1 (segunda) a 7 (domingo).')
    if any(isinstance(dia, bool) or not isinstance(dia, int) or dia not in DIAS_DA_SEMANA for dia in valor):
        raise ValidationError('Cada dia de funcionamento deve ser um número de 1 (segunda) a 7 (domingo).')
    if not valor:
        raise ValidationError('Escolha ao menos um dia de funcionamento.')
    return sorted(set(valor))


class Barbershop(TimeStampedModel):
    """
    Representa uma barbearia cadastrada na plataforma — o tenant. Todo
    o restante do sistema gira em torno deste modelo: usuários, barbeiros,
    serviços e agendamentos são sempre vinculados a uma barbearia.
    """
    nome = models.CharField('nome', max_length=150)
    endereco = models.CharField('endereço', max_length=255)
    telefone = models.CharField('telefone', max_length=20)
    email = models.EmailField('e-mail')
    horario_abertura = models.TimeField('horário de abertura')
    horario_fechamento = models.TimeField('horário de fechamento')
    logo = models.ImageField(
        'logo', upload_to='barbershops/logos/', null=True, blank=True,
    )
    ativo = models.BooleanField('ativo', default=True)
    # Dias da semana em que a barbearia atende (ISO: 1 = segunda ... 7 = domingo).
    # O padrão são todos os dias, para não fechar nenhum dia de barbearias
    # já cadastradas: cada uma configura os seus em "Dados da barbearia".
    dias_funcionamento = models.JSONField(
        'dias de funcionamento',
        default=todos_os_dias,
        help_text='Dias da semana em que a barbearia atende: 1 = segunda-feira ... 7 = domingo.',
    )

    class Meta:
        verbose_name = 'barbearia'
        verbose_name_plural = 'barbearias'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def clean(self):
        """Horário de funcionamento coerente e dias válidos (vale para API e Django Admin)."""
        super().clean()
        errors = {}
        if (
            self.horario_abertura is not None
            and self.horario_fechamento is not None
            and self.horario_fechamento <= self.horario_abertura
        ):
            errors['horario_fechamento'] = HORARIO_INVALIDO_MENSAGEM
        try:
            self.dias_funcionamento = validar_dias_funcionamento(self.dias_funcionamento)
        except ValidationError as error:
            errors['dias_funcionamento'] = error.messages
        if errors:
            raise ValidationError(errors)

    def abre_no_dia(self, data):
        """Verdadeiro se a barbearia atende no dia da semana de `data` (um `date`)."""
        return data.isoweekday() in (self.dias_funcionamento or [])


class Barber(TimeStampedModel):
    """
    Dados profissionais de um barbeiro dentro de uma barbearia
    específica. Liga um User (com tipo_perfil='barbeiro') à barbearia
    em que ele atua.

    OneToOneField em `user`: cada usuário barbeiro atua em uma única
    barbearia, consistente com o restante da arquitetura multi-tenant
    (um usuário pertence a uma barbearia só).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='usuário',
        related_name='perfil_barbeiro',
        on_delete=models.PROTECT,
    )
    barbershop = models.ForeignKey(
        Barbershop,
        verbose_name='barbearia',
        related_name='barbeiros',
        on_delete=models.PROTECT,
    )
    especialidade = models.CharField('especialidade', max_length=150, blank=True)
    ativo = models.BooleanField('ativo', default=True)
    deleted_at = models.DateTimeField('deleted_at', null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='deleted_by',
        null=True,
        blank=True,
        related_name='barber_deletions',
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'barbeiro'
        verbose_name_plural = 'barbeiros'
        ordering = ['user__nome']
        indexes = [
            models.Index(fields=['barbershop', 'ativo']),
            models.Index(fields=['barbershop', 'user']),
        ]

    def __str__(self):
        return f'{self.user.nome} - {self.barbershop.nome}'

    def clean(self):
        """Mantém o perfil profissional no mesmo tenant do seu usuário."""
        super().clean()
        if not self.user_id:
            return

        # Import local evita dependência circular durante o carregamento dos
        # modelos (accounts referencia Barbershop por string).
        from accounts.models import User

        errors = {}
        if self.ativo and self.user.tipo_perfil != User.TipoPerfil.BARBEIRO:
            errors['user'] = 'O usuário vinculado deve ter perfil de barbeiro.'
        if self.barbershop_id and self.user.barbershop_id != self.barbershop_id:
            errors['barbershop'] = (
                'A barbearia do barbeiro deve ser a mesma do usuário vinculado.'
            )
        if errors:
            raise ValidationError(errors)
