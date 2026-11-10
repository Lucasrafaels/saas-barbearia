# Data migration to populate preco_historico for existing appointments.
# Uses current service price as an estimate since the original price is lost.
# This is documented as "estimated" values.

from django.db import migrations


def populate_preco_historico(apps, schema_editor):
    """Populate preco_historico using current service price as estimate."""
    Appointment = apps.get_model('appointments', 'Appointment')
    for appointment in Appointment.objects.filter(preco_historico__isnull=True).select_related('servico'):
        if appointment.servico_id:
            appointment.preco_historico = appointment.servico.preco
            appointment.save(update_fields=['preco_historico'])


def reverse_populate_preco_historico(apps, schema_editor):
    """Reverse: set preco_historico back to null."""
    Appointment = apps.get_model('appointments', 'Appointment')
    Appointment.objects.all().update(preco_historico=None)


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0007_appointment_preco_historico'),
    ]

    operations = [
        migrations.RunPython(populate_preco_historico, reverse_populate_preco_historico),
    ]