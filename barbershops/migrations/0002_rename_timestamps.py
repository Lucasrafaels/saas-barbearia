from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('barbershops', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='barbershop',
            old_name='criado_em',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='barbershop',
            old_name='atualizado_em',
            new_name='updated_at',
        ),
        migrations.RenameField(
            model_name='barber',
            old_name='criado_em',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='barber',
            old_name='atualizado_em',
            new_name='updated_at',
        ),
    ]
