"""
Modelo de serviços oferecidos por cada barbearia (corte, barba, etc.).
"""
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

    class Meta:
        verbose_name = 'serviço'
        verbose_name_plural = 'serviços'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.barbershop.nome})'
