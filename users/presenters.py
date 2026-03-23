from dataclasses import dataclass

from .domain.loyalty import LoyaltyProgram


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


def build_customer_dashboard_view_model(user, *, qr_code_image: str | None, dashboard_url: str, logout_url: str) -> dict:
    program = LoyaltyProgram()
    cards = [
        DashboardCard(key='role', label='Роль', value=user.get_role_display()),
        DashboardCard(key='phone', label='Телефон', value=user.phone),
        DashboardCard(key='coffee_count', label='Кофе по акции', value=program.render_progress(user.coffee_count)),
        DashboardCard(key='loyalty_status', label='Статус акции', value=user.loyalty_status_text),
        DashboardCard(key='qr_code_uuid', label='UUID для QR', value=str(user.qr_code_uuid) if user.qr_code_uuid else 'QR-код еще не создан.'),
    ]
    actions = [
        DashboardAction(label='Создать или обновить QR-код', method='post', url=dashboard_url),
        DashboardAction(label='Выйти', method='post', url=logout_url),
    ]
    return {
        'heading': 'Личный кабинет',
        'description': 'Здесь можно выпускать и перевыпускать персональный QR-код пользователя.',
        'cards': cards,
        'actions': actions,
        'links': [],
        'qr_code_image': qr_code_image,
        'state_url': '/auth/dashboard/state/',
        'live_updates_enabled': True,
    }


def build_barista_dashboard_view_model(user, *, barista_url: str, logout_url: str) -> dict:
    cards = [
        DashboardCard(key='role', label='Роль', value=user.get_role_display()),
        DashboardCard(key='phone', label='Телефон', value=user.phone),
    ]
    actions = [
        DashboardAction(label='Выйти', method='post', url=logout_url),
    ]
    links = [
        DashboardAction(label='Открыть кабинет баристы', method='get', url=barista_url),
    ]
    return {
        'heading': 'Личный кабинет',
        'description': 'У баристы отдельный экран для сканирования QR-кодов клиентов.',
        'cards': cards,
        'actions': actions,
        'links': links,
        'qr_code_image': None,
        'state_url': '',
        'live_updates_enabled': False,
    }


def build_scan_result_view_model(customer, loyalty_state) -> dict:
    program = LoyaltyProgram()
    return {
        'customer_phone': customer.phone,
        'progress': program.render_progress(customer.coffee_count),
        'barista_message': loyalty_state.barista_message,
    }
