from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from rest_framework_simplejwt.exceptions import TokenError

from .api import clear_auth_cookies, set_auth_cookies
from .authentication import get_user_from_access_cookie
from .forms import LoginForm, PasswordResetConfirmForm, PasswordResetRequestForm, RegisterForm
from .models import User
from .services import issue_password_reset_code, issue_tokens_for_user, revoke_refresh_token


class AuthenticatedTemplateView(View):
    template_name = ''

    def get_authenticated_user(self, request: HttpRequest):
        return get_user_from_access_cookie(request)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.auth_user = self.get_authenticated_user(request)
        if self.auth_user is None:
            messages.error(request, 'Сначала войдите в аккаунт.')
            return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)


class LoginView(View):
    template_name = 'auth/login.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        if get_user_from_access_cookie(request):
            return redirect('users:dashboard')
        return render(request, self.template_name, {'form': LoginForm(request=request)})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = LoginForm(request=request, data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form}, status=400)

        tokens = issue_tokens_for_user(form.get_user(), request)
        response = redirect('users:dashboard')
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        messages.success(request, 'Вы успешно вошли.')
        return response


class RegisterView(View):
    template_name = 'auth/register.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        if get_user_from_access_cookie(request):
            return redirect('users:dashboard')
        return render(request, self.template_name, {'form': RegisterForm()})

    @transaction.atomic
    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form}, status=400)

        user = form.save()
        tokens = issue_tokens_for_user(user, request)
        response = redirect('users:dashboard')
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        messages.success(request, 'Аккаунт создан.')
        return response


class LogoutView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                revoke_refresh_token(refresh_token)
            except TokenError:
                pass
        response = redirect('users:login')
        clear_auth_cookies(response)
        messages.success(request, 'Вы вышли из аккаунта.')
        return response


class DashboardView(AuthenticatedTemplateView):
    template_name = 'auth/dashboard.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {'auth_user': self.auth_user})


class PasswordResetView(View):
    template_name = 'auth/password_reset.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                'request_form': PasswordResetRequestForm(),
                'confirm_form': PasswordResetConfirmForm(),
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get('action')
        request_form = PasswordResetRequestForm()
        confirm_form = PasswordResetConfirmForm()

        if action == 'request':
            request_form = PasswordResetRequestForm(request.POST)
            if request_form.is_valid():
                reset_data = issue_password_reset_code(request_form.cleaned_data['phone'])
                messages.success(request, 'Если пользователь существует, код отправлен.')
                if settings.DEBUG and reset_data is not None:
                    messages.info(request, f"Тестовый код: {reset_data['code']}")
                    messages.info(request, 'В production сюда подключается SMS-провайдер.')
                return redirect('users:password_reset')
        elif action == 'confirm':
            confirm_form = PasswordResetConfirmForm(request.POST)
            if confirm_form.is_valid():
                target_user = User.objects.get(phone=confirm_form.cleaned_data['phone'])
                reset_record = target_user.password_reset_codes.filter(used_at__isnull=True).first()
                target_user.set_password(confirm_form.cleaned_data['password1'])
                target_user.save(update_fields=['password'])
                if reset_record:
                    reset_record.mark_used()
                messages.success(request, 'Пароль обновлен.')
                return redirect('users:login')

        return render(
            request,
            self.template_name,
            {
                'request_form': request_form,
                'confirm_form': confirm_form,
            },
            status=400,
        )
