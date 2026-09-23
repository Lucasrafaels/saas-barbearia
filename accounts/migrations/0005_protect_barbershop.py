# Generated manually to preserve tenant data when a barbershop is removed.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_user_created_at_alter_user_updated_at'),
        ('barbershops', '0003_alter_barber_created_at_alter_barber_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='barbershop',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='usuarios',
                to='barbershops.barbershop',
                verbose_name='barbearia',
            ),
        ),
    ]
