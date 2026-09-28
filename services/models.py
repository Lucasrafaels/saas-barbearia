"""
Modelo de serviços oferecidos por cada barbearia (corte, barba, etc.).
"""
from django.conf import settings
from django.db import models

from config.models import TimeStampedModel


class Service(TimeStampedModel):
    barbershop = models.ForeignKey(
        'barbershops.Barbershop',
        verbose_name='barbearia',
        related_name='servicos',
        on_delete=models.PROTECT,
    )
    nome = models.CharField('nome', max_length=150)
    descricao = models.TextField('descrição', blank=True)
    preco = models.DecimalField('preço', max_digits=8, decimal_places=2)
    duracao = models.PositiveIntegerField(
        'duração (minutos)',
        help_text='Duração estimada do serviço, em minutos.',
    )
    ativo = models.BooleanField('ativo', default=True)
    deleted_at = models.DateTimeField('deleted_at', null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='deleted_by',
        null=True,
        blank=True,
        related_name='service_deletions',
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'serviço'
        verbose_name_plural = 'serviços'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['barbershop', 'ativo']),
            models.Index(fields=['barbershop', 'duracao']),
        ]

    def __str__(self):
        return f'{self.nome} ({self.barbershop.nome})'
