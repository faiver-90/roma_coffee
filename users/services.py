import base64
import io
import uuid
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
import qrcode
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .domain.loyalty import LoyaltyService
from .domain.roles import UserRole
from .models import PasswordResetCode, RefreshSession, User


def get_client_ip(request) -> str | None:
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def issue_tokens_for_user(user: User, request):
    access_token = AccessToken.for_user(user)
    refresh_token = RefreshToken.for_user(user)
    refresh_session = RefreshSession.create_from_token(
        user=user,
        token=str(refresh_token),
        jti=refresh_token['jti'],
        expires_at=datetime.fromtimestamp(refresh_token['exp'], tz=dt_timezone.utc),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        ip_address=get_client_ip(request),
    )
    return {
        'access': str(access_token),
        'refresh': str(refresh_token),
        'session': refresh_session,
    }


def rotate_refresh_token(refresh_token: str, request):
    token = RefreshToken(refresh_token)
    session = RefreshSession.objects.filter(jti=token['jti']).select_related('user').first()
    if session is None or not session.is_active() or not session.matches(refresh_token):
        raise ValueError('Refresh session is invalid.')

    session.revoke()
    return issue_tokens_for_user(session.user, request)


def revoke_refresh_token(refresh_token: str) -> None:
    token = RefreshToken(refresh_token)
    session = RefreshSession.objects.filter(jti=token['jti']).first()
    if session:
        session.revoke()


def issue_password_reset_code(phone: str):
    user = User.objects.filter(phone=phone).first()
    if user is None:
        return None

    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    reset_record, code = PasswordResetCode.issue_for_user(user)
    return {'user': user, 'record': reset_record, 'code': code}


def regenerate_user_qr_code(user: User) -> User:
    user.qr_code_uuid = uuid.uuid4()
    user.qr_code_updated_at = timezone.now()
    user.save(update_fields=['qr_code_uuid', 'qr_code_updated_at'])
    return user


def build_qr_code_image_base64(value: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(value)
    qr.make(fit=True)

    image = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def scan_customer_loyalty(customer: User):
    loyalty_service = LoyaltyService()
    result = loyalty_service.scan(
        count=customer.coffee_count,
        reward_available=customer.free_coffee_available,
    )
    customer.coffee_count = 0 if result.reset_applied else min(customer.coffee_count + 1, loyalty_service.program.required_paid_coffees)
    customer.free_coffee_available = result.reward_available
    customer.loyalty_status = result.status
    customer.save(update_fields=['coffee_count', 'free_coffee_available', 'loyalty_status'])
    return result


def get_customer_by_qr_code(qr_code_uuid):
    return User.objects.filter(qr_code_uuid=qr_code_uuid, role=UserRole.CUSTOMER).first()
