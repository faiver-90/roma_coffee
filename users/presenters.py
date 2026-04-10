from dataclasses import dataclass

from .domain.loyalty import LoyaltyProgram, LoyaltyStatus


@dataclass(frozen=True)
class DashboardCard:
    key: str
    label: str
    value: str


@dataclass(frozen=True)
class DashboardAction:
    label: str
    method: str
    url: str


@dataclass(frozen=True)
class CelebrationModal:
    title: str
    message: str
    accent: str


def build_customer_celebration_modal(user) -> CelebrationModal | None:
    status = LoyaltyStatus(user.loyalty_status)
    if status == LoyaltyStatus.REWARD_REDEEMED:
        return CelebrationModal(
            title='Сделаем кофе бесплатно!!!',
            message='Спасибо что вы выпили первые 6 у нас!!!',
            accent='gold',
        )
    if status == LoyaltyStatus.REWARD_READY:
        return CelebrationModal(
            title='Бонус открыт',
            message='Следующий кофе бесплатно!',
            accent='cream',
        )
    return None


def build_barista_celebration_modal(loyalty_state) -> CelebrationModal | None:
    program = LoyaltyProgram()
    if loyalty_state.barista_message != program.barista_make_free_message:
        return None
    return CelebrationModal(
        title='Подарочный кофе',
        message=program.barista_make_free_message,
        accent='gold',
    )


def build_customer_dashboard_view_model(user, *, qr_code_image: str | None, dashboard_url: str, logout_url: str) -> dict:
    program = LoyaltyProgram()
    cards = [
        DashboardCard(key='coffee_count', label='Кофе по акции', value=program.render_progress(user.coffee_count)),
    ]
    actions = [
        DashboardAction(label='Создать или обновить QR-код', method='post', url=dashboard_url),
        DashboardAction(label='Выйти', method='post', url=logout_url),
    ]
    return {
        'heading': 'Личный кабинет',
        'cards': cards,
        'actions': actions,
        'links': [],
        'qr_code_image': qr_code_image,
        'state_url': '/auth/dashboard/state/',
        'live_updates_enabled': True,
        'celebration_modal': build_customer_celebration_modal(user),
        'qr_refresh_url': f'{dashboard_url}qr/',
    }


def build_barista_dashboard_view_model(user, *, qr_code_image: str | None, dashboard_url: str, barista_url: str, logout_url: str) -> dict:
    cards = [
        DashboardCard(key='role', label='Роль', value=user.get_role_display()),
        DashboardCard(key='qr_code_uuid', label='UUID для QR', value=str(user.qr_code_uuid) if user.qr_code_uuid else 'QR-код еще не создан.'),
    ]
    actions = [
        DashboardAction(label='Создать или обновить QR-код', method='post', url=dashboard_url),
        DashboardAction(label='Выйти', method='post', url=logout_url),
    ]
    links = [
        DashboardAction(label='Открыть кабинет бариста', method='get', url=barista_url),
    ]
    return {
        'heading': 'Личный кабинет',
        'description': 'У бариста отдельный экран для сканирования QR-кодов клиентов.',
        'cards': cards,
        'actions': actions,
        'links': links,
        'qr_code_image': qr_code_image,
        'state_url': '',
        'live_updates_enabled': False,
        'celebration_modal': None,
        'qr_refresh_url': f'{dashboard_url}qr/',
    }


def build_scan_result_view_model(customer, loyalty_state) -> dict:
    program = LoyaltyProgram()
    celebration_modal = build_barista_celebration_modal(loyalty_state)
    return {
        'customer_phone': customer.formatted_phone,
        'progress': program.render_progress(customer.coffee_count),
        'barista_message': loyalty_state.barista_message,
        'celebration_modal': (
            {
                'title': celebration_modal.title,
                'message': celebration_modal.message,
                'accent': celebration_modal.accent,
            }
            if celebration_modal is not None
            else None
        ),
    }
