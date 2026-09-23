# Generated manually to retain users and tenant data referenced by a barber.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_protect_barbershop'),
        ('barbershops', '0003_alter_barber_created_at_alter_barber_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='barber',
            name='barbershop',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='barbeiros',
                to='barbershops.barbershop',
                verbose_name='barbearia',
            ),
        ),
        migrations.AlterField(
            model_name='barber',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='perfil_barbeiro',
                to='accounts.user',
                verbose_name='usuário',
            ),
        ),
    ]
