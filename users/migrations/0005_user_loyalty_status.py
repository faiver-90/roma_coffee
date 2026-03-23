from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_user_roles_and_loyalty'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='loyalty_status',
            field=models.CharField(default='collecting', max_length=32),
        ),
    ]
