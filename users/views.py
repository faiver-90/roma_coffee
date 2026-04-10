from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from rest_framework_simplejwt.exceptions import TokenError

from .api import clear_auth_cookies, set_auth_cookies
from .authentication import get_user_from_access_cookie
from .domain.roles import UserRole
from .forms_barista import BaristaScanForm
from .forms import AdminStatsFilterForm, LoginForm, PasswordResetConfirmForm, PasswordResetRequestForm, RegisterForm
from .models import ScanEvent, User
from .presenters import (
    build_barista_dashboard_view_model,
    build_customer_dashboard_view_model,
    build_scan_result_view_model,
)
from .services import (
    build_qr_code_image_base64,
    get_customer_by_qr_code,
    issue_password_reset_code,
    issue_tokens_for_user,
    regenerate_user_qr_code,
    revoke_refresh_token,
    scan_customer_loyalty,
)


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


class RoleRequiredView(AuthenticatedTemplateView):
    required_role = None
    denied_redirect_name = 'users:dashboard'

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        if not hasattr(self, 'auth_user') or self.auth_user is None:
            return response
        allowed_roles = self.required_role
        if allowed_roles is not None and not isinstance(allowed_roles, (tuple, list, set, frozenset)):
            allowed_roles = (allowed_roles,)
        if allowed_roles is not None and self.auth_user.role not in allowed_roles:
            messages.error(request, 'Недостаточно прав для этого раздела.')
            return redirect(self.denied_redirect_name)
        return response


class LoginView(View):
    template_name = 'auth/login.html'

    @staticmethod
    def get_success_url(user) -> str:
        if user.is_admin:
            return 'users:barista_dashboard'
        if user.is_barista:
            return 'users:barista_dashboard'
        return 'users:dashboard'

    def get(self, request: HttpRequest) -> HttpResponse:
        user = get_user_from_access_cookie(request)
        if user:
            return redirect(self.get_success_url(user))
        return render(request, self.template_name, {'form': LoginForm(request=request)})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = LoginForm(request=request, data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form}, status=400)

        tokens = issue_tokens_for_user(form.get_user(), request)
        response = redirect(self.get_success_url(form.get_user()))
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
        if self.auth_user.is_admin:
            return redirect('users:barista_dashboard')

        qr_code_image = None
        if self.auth_user.qr_code_uuid:
            qr_code_image = build_qr_code_image_base64(str(self.auth_user.qr_code_uuid))
        context = (
            build_barista_dashboard_view_model(
                self.auth_user,
                qr_code_image=qr_code_image,
                dashboard_url=reverse('users:dashboard'),
                barista_url=reverse('users:barista_dashboard'),
                logout_url=reverse('users:logout'),
            )
            if self.auth_user.is_barista
            else build_customer_dashboard_view_model(
                self.auth_user,
                qr_code_image=qr_code_image,
                dashboard_url=reverse('users:dashboard'),
                logout_url=reverse('users:logout'),
            )
        )
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        regenerate_user_qr_code(self.auth_user)
        messages.success(request, 'QR-код обновлен.')
        return redirect('users:dashboard')


class DashboardStateView(AuthenticatedTemplateView):
    def get(self, request: HttpRequest) -> HttpResponse:
        if self.auth_user.is_barista:
            return JsonResponse(
                {
                    'role': self.auth_user.get_role_display(),
                    'phone': self.auth_user.formatted_phone,
                }
            )

        context = build_customer_dashboard_view_model(
            self.auth_user,
            qr_code_image=None,
            dashboard_url=reverse('users:dashboard'),
            logout_url=reverse('users:logout'),
        )
        card_map = {card.key: card.value for card in context['cards']}
        if context['celebration_modal'] is not None:
            card_map['celebration_modal'] = {
                'title': context['celebration_modal'].title,
                'message': context['celebration_modal'].message,
                'accent': context['celebration_modal'].accent,
            }
        else:
            card_map['celebration_modal'] = None
        return JsonResponse(card_map)


class DashboardQrRefreshView(AuthenticatedTemplateView):
    def post(self, request: HttpRequest) -> HttpResponse:
        regenerate_user_qr_code(self.auth_user)
        return JsonResponse(
            {
                'qr_code_uuid': str(self.auth_user.qr_code_uuid),
                'qr_code_image': build_qr_code_image_base64(str(self.auth_user.qr_code_uuid)),
            }
        )


class BaristaDashboardView(RoleRequiredView):
    required_role = (UserRole.BARISTA, UserRole.ADMIN)
    template_name = 'auth/barista_dashboard.html'
    session_key = 'barista_scan_result'

    def get(self, request: HttpRequest) -> HttpResponse:
        scan_result = request.session.pop(self.session_key, None)
        return render(
            request,
            self.template_name,
            {
                'form': BaristaScanForm(),
                'scan_result': scan_result,
                'show_stats_link': self.auth_user.is_admin,
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = BaristaScanForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'scan_result': None}, status=400)

        customer = get_customer_by_qr_code(form.cleaned_data['qr_code_uuid'])
        if customer is None:
            form.add_error('qr_code_uuid', 'Пользователь с таким QR-кодом не найден.')
            return render(request, self.template_name, {'form': form, 'scan_result': None}, status=404)

        loyalty_state = scan_customer_loyalty(customer, barista=self.auth_user)
        messages.success(request, loyalty_state.barista_message)
        request.session[self.session_key] = build_scan_result_view_model(customer, loyalty_state)
        return redirect('users:barista_dashboard')


class AdminDashboardView(RoleRequiredView):
    required_role = UserRole.ADMIN
    template_name = 'auth/admin_dashboard.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        form = AdminStatsFilterForm(request.GET or None)
        stats = {
            'total_scans': 0,
            'gifted_scans': 0,
        }

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            today = timezone.localdate()
            start_date = today - timedelta(days=29)
            end_date = today

        queryset = ScanEvent.objects.filter(
            scanned_at__date__gte=start_date,
            scanned_at__date__lte=end_date,
        )
        aggregated = queryset.aggregate(
            total_scans=Count('id'),
            gifted_scans=Count('id', filter=Q(is_gifted=True)),
        )
        stats.update(aggregated)

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'stats': stats,
                'start_date': start_date,
                'end_date': end_date,
            },
        )


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
