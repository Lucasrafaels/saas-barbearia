from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='criado_em',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='atualizado_em',
            new_name='updated_at',
        ),
    ]
