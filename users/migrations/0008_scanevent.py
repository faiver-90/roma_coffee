from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0007_add_admin_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScanEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_gifted', models.BooleanField(default=False)),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('barista', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_scan_events', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scan_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-scanned_at'],
            },
        ),
    ]
