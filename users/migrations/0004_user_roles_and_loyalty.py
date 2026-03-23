from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_merge_20260323_1834'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='coffee_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='free_coffee_available',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('customer', 'Обычный пользователь'), ('barista', 'Бариста')],
                default='customer',
                max_length=16,
            ),
        ),
    ]
