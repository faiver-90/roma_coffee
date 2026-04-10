from django.db import models


class UserRole(models.TextChoices):
    CUSTOMER = 'customer', 'Обычный пользователь'
    BARISTA = 'barista', 'Бариста'
    ADMIN = 'admin', 'Администратор'
