"""
Modelos relacionados à barbearia em si (o "tenant" do sistema) e aos
barbeiros vinculados a ela.
"""
from django.conf import settings
from django.db import models

from config.models import TimeStampedModel


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

    class Meta:
        verbose_name = 'barbearia'
        verbose_name_plural = 'barbearias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


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
        on_delete=models.CASCADE,
    )
    barbershop = models.ForeignKey(
        Barbershop,
        verbose_name='barbearia',
        related_name='barbeiros',
        on_delete=models.CASCADE,
    )
    especialidade = models.CharField('especialidade', max_length=150, blank=True)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'barbeiro'
        verbose_name_plural = 'barbeiros'
        ordering = ['user__nome']

    def __str__(self):
        return f'{self.user.nome} - {self.barbershop.nome}'
