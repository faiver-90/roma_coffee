from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetCode, RefreshSession, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('-date_joined',)
    list_display = (
        'phone',
        'role',
        'coffee_count',
        'free_coffee_available',
        'loyalty_status',
        'qr_code_uuid',
        'is_active',
        'is_staff',
        'date_joined',
    )
    list_filter = ('role', 'free_coffee_available', 'loyalty_status', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('phone', 'qr_code_uuid')
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Role', {'fields': ('role',)}),
        (
            'Loyalty',
            {
                'fields': (
                    'coffee_count',
                    'free_coffee_available',
                    'loyalty_status',
                )
            },
        ),
        (
            'QR',
            {
                'fields': (
                    'qr_code_uuid',
                    'qr_code_updated_at',
                )
            },
        ),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'phone',
                    'password1',
                    'password2',
                    'role',
                    'coffee_count',
                    'free_coffee_available',
                    'loyalty_status',
                    'qr_code_uuid',
                    'qr_code_updated_at',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )


@admin.register(RefreshSession)
class RefreshSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'jti', 'expires_at', 'revoked_at', 'created_at')
    search_fields = ('user__phone', 'jti')
    readonly_fields = ('token_hash', 'created_at')


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at', 'created_at')
    search_fields = ('user__phone',)
    readonly_fields = ('code_hash', 'created_at')
