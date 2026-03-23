from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetCode, RefreshSession, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('-date_joined',)
    list_display = ('phone', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('phone',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('phone', 'password1', 'password2', 'is_staff', 'is_superuser'),
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
