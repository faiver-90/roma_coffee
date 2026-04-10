from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0006_normalize_phone_storage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('customer', 'Обычный пользователь'),
                    ('barista', 'Бариста'),
                    ('admin', 'Администратор'),
                ],
                default='customer',
                max_length=16,
            ),
        ),
    ]
