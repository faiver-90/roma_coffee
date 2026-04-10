import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .domain.loyalty import LoyaltyProgram, LoyaltyStatus
from .domain.roles import UserRole
from .utils import format_phone, normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone: str, password: str | None, **extra_fields):
        if not phone:
            raise ValueError('The phone field must be set.')
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone: str, password: str, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone, password, **extra_fields)

    def get_by_natural_key(self, username):
        canonical = normalize_phone(username)
        formatted = format_phone(canonical)
        return self.get(Q(phone=canonical) | Q(phone=formatted))


class User(AbstractBaseUser, PermissionsMixin):
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.CUSTOMER)
    coffee_count = models.PositiveSmallIntegerField(default=0)
    free_coffee_available = models.BooleanField(default=False)
    loyalty_status = models.CharField(max_length=32, default=LoyaltyStatus.COLLECTING)
    phone = models.CharField(max_length=32, unique=True)
    qr_code_uuid = models.UUIDField(unique=True, null=True, blank=True)
    qr_code_updated_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ['-date_joined']

    def __str__(self) -> str:
        return self.phone

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    @property
    def formatted_phone(self) -> str:
        return format_phone(self.phone)

    @property
    def is_barista(self) -> bool:
        return self.role == UserRole.BARISTA

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def loyalty_status_text(self) -> str:
        program = LoyaltyProgram()
        return program.message_for_status(LoyaltyStatus(self.loyalty_status))


class RefreshSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refresh_sessions',
    )
    jti = models.CharField(max_length=64, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def create_from_token(
        cls,
        *,
        user,
        token: str,
        jti: str,
        expires_at,
        user_agent: str = '',
        ip_address: str | None = None,
    ):
        return cls.objects.create(
            user=user,
            jti=jti,
            token_hash=cls.hash_token(token),
            expires_at=expires_at,
            user_agent=user_agent[:255],
            ip_address=ip_address,
        )

    def matches(self, token: str) -> bool:
        return secrets.compare_digest(self.token_hash, self.hash_token(token))

    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])


class PasswordResetCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_codes',
    )
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    @classmethod
    def issue_for_user(cls, user, *, lifetime_minutes: int = 10):
        code = f'{secrets.randbelow(1000000):06d}'
        record = cls.objects.create(
            user=user,
            code_hash=cls.hash_code(code),
            expires_at=timezone.now() + timezone.timedelta(minutes=lifetime_minutes),
        )
        return record, code

    def is_active(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def matches(self, code: str) -> bool:
        return secrets.compare_digest(self.code_hash, self.hash_code(code))

    def mark_used(self) -> None:
        if self.used_at is None:
            self.used_at = timezone.now()
            self.save(update_fields=['used_at'])


class ScanEvent(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_events',
    )
    barista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_scan_events',
    )
    is_gifted = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
