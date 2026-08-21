from django.db import models

class TimeStampedModel(models.Model):
    """
    Modelo abstrato que adiciona campos de criação e atualização.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True