# Generated manually to prevent appointment history from being cascaded away.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_protect_barbershop'),
        ('barbershops', '0004_protect_barber_history'),
        ('services', '0004_protect_service_history'),
        ('appointments', '0003_alter_appointment_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='barbeiro',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='agendamentos',
                to='barbershops.barber',
                verbose_name='barbeiro',
            ),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='barbershop',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='agendamentos',
                to='barbershops.barbershop',
                verbose_name='barbearia',
            ),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='cliente',
            field=models.ForeignKey(
                limit_choices_to={'tipo_perfil': 'cliente'},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='agendamentos_cliente',
                to='accounts.user',
                verbose_name='cliente',
            ),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='servico',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='agendamentos',
                to='services.service',
                verbose_name='serviço',
            ),
        ),
    ]
