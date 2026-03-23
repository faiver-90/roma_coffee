from django.urls import path

from .api import (
    LoginApiView,
    LogoutApiView,
    MeApiView,
    PasswordResetConfirmApiView,
    PasswordResetRequestApiView,
    RefreshApiView,
    RegisterApiView,
)
from .views import BaristaDashboardView, DashboardView, LoginView, LogoutView, PasswordResetView, RegisterView

app_name = 'users'

urlpatterns = [
    path('barista/', BaristaDashboardView.as_view(), name='barista_dashboard'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('api/register/', RegisterApiView.as_view(), name='api_register'),
    path('api/login/', LoginApiView.as_view(), name='api_login'),
    path('api/refresh/', RefreshApiView.as_view(), name='api_refresh'),
    path('api/logout/', LogoutApiView.as_view(), name='api_logout'),
    path('api/me/', MeApiView.as_view(), name='api_me'),
    path('api/password-reset/', PasswordResetRequestApiView.as_view(), name='api_password_reset'),
    path('api/password-reset/confirm/', PasswordResetConfirmApiView.as_view(), name='api_password_reset_confirm'),
]
