"""
Modelos abstratos compartilhados entre os apps do projeto.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """
    Modelo base abstrato que adiciona campos de auditoria (data de
    criação e de última atualização) a qualquer modelo que o herdar.
    """
    criado_em = models.DateTimeField('criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        abstract = True
