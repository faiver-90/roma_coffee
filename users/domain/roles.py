from django.db import models


class UserRole(models.TextChoices):
    CUSTOMER = 'customer', 'Обычный пользователь'
    BARISTA = 'barista', 'бариста'
    ADMIN = 'admin', 'Администратор'
