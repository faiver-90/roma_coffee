from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


def get_user_from_access_cookie(request):
    raw_token = request.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)
    if not raw_token:
        return None

    auth = JWTAuthentication()
    try:
        validated_token = auth.get_validated_token(raw_token)
    except (InvalidToken, TokenError):
        return None

    user_id = validated_token.get('user_id')
    if not user_id:
        return None

    return User.objects.filter(id=user_id, is_active=True).first()
