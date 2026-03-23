from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from .forms import LoginForm, PasswordResetConfirmForm, PasswordResetRequestForm, RegisterForm
from .services import issue_password_reset_code, issue_tokens_for_user, revoke_refresh_token, rotate_refresh_token

User = get_user_model()


def set_auth_cookies(response: Response, *, access: str, refresh: str) -> None:
    response.set_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=False,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.AUTH_ACCESS_COOKIE_NAME)
    response.delete_cookie(settings.AUTH_REFRESH_COOKIE_NAME)


class RegisterApiView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        form = RegisterForm(request.data)
        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = form.save()
        tokens = issue_tokens_for_user(user, request)
        response = Response(
            {'access': tokens['access'], 'user': {'id': user.id, 'phone': user.phone}},
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        return response


class LoginApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        form = LoginForm(request=request, data=request.data)
        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = form.get_user()
        tokens = issue_tokens_for_user(user, request)
        response = Response({'access': tokens['access'], 'user': {'id': user.id, 'phone': user.phone}})
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        return response


class RefreshApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME) or request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tokens = rotate_refresh_token(refresh_token, request)
        except (TokenError, ValueError):
            return Response({'detail': 'Refresh token is invalid.'}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({'access': tokens['access']})
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        return response


class LogoutApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME) or request.data.get('refresh')
        if refresh_token:
            try:
                revoke_refresh_token(refresh_token)
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'id': request.user.id, 'phone': request.user.phone})


class PasswordResetRequestApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        form = PasswordResetRequestForm(request.data)
        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        reset_data = issue_password_reset_code(form.cleaned_data['phone'])
        payload = {'detail': 'Если пользователь существует, код отправлен.'}
        if settings.DEBUG and reset_data is not None:
            payload['debug_code'] = reset_data['code']
        return Response(payload)


class PasswordResetConfirmApiView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        form = PasswordResetConfirmForm(request.data)
        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(phone=form.cleaned_data['phone'])
        reset_record = user.password_reset_codes.filter(used_at__isnull=True).first()
        user.set_password(form.cleaned_data['password1'])
        user.save(update_fields=['password'])
        if reset_record:
            reset_record.mark_used()
        return Response({'detail': 'Пароль обновлен.'})
