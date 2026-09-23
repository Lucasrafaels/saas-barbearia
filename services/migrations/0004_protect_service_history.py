# Generated manually to retain service records referenced by appointments.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('barbershops', '0004_protect_barber_history'),
        ('services', '0003_alter_service_created_at_alter_service_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='barbershop',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='servicos',
                to='barbershops.barbershop',
                verbose_name='barbearia',
            ),
        ),
    ]
