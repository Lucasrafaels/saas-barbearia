from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='service',
            old_name='criado_em',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='service',
            old_name='atualizado_em',
            new_name='updated_at',
        ),
    ]
