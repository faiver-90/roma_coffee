from django.db import migrations


def normalize_phone_value(value: str) -> str:
    digits = "".join(char for char in (value or "") if char.isdigit())
    if len(digits) == 10:
        digits = f"7{digits}"
    elif digits.startswith("8") and len(digits) == 11:
        digits = f"7{digits[1:]}"
    if len(digits) != 11 or not digits.startswith("7"):
        return value
    return f"+{digits}"


def forward(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all().iterator():
        normalized_phone = normalize_phone_value(user.phone)
        if normalized_phone != user.phone:
            User.objects.filter(pk=user.pk).update(phone=normalized_phone)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_user_loyalty_status"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
