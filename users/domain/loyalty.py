from dataclasses import dataclass
from enum import StrEnum


class LoyaltyStatus(StrEnum):
    COLLECTING = 'collecting'
    REWARD_READY = 'reward_ready'
    REWARD_REDEEMED = 'reward_redeemed'


@dataclass(frozen=True)
class LoyaltyProgram:
    required_paid_coffees: int = 6
    reward_name: str = 'кофе'
    reward_ready_message: str = 'Следующий кофе бесплатно!'
    reward_redeemed_message: str = 'Спасибо что вы выпили первые 6 у нас!!!'
    progress_template: str = '{count}/{goal}'
    barista_progress_template: str = 'Отметка засчитана. Сейчас у пользователя {count}/{goal} кофе.'
    barista_reward_ready_message: str = 'Следующий кофе для этого пользователя будет бесплатным.'
    barista_make_free_message: str = 'Сделать бесплатный кофе!'

    @property
    def reset_count(self) -> int:
        return 0

    def render_progress(self, count: int) -> str:
        return self.progress_template.format(count=count, goal=self.required_paid_coffees)

    def message_for_status(self, status: LoyaltyStatus) -> str:
        if status == LoyaltyStatus.REWARD_READY:
            return self.reward_ready_message
        if status == LoyaltyStatus.REWARD_REDEEMED:
            return self.reward_redeemed_message
        return f'Собирайте {self.required_paid_coffees} кофе, чтобы получить следующий бесплатно.'


@dataclass(frozen=True)
class LoyaltyState:
    progress_text: str
    status: LoyaltyStatus
    customer_message: str
    barista_message: str
    reward_available: bool
    reset_applied: bool


class LoyaltyService:
    def __init__(self, program: LoyaltyProgram | None = None):
        self.program = program or LoyaltyProgram()

    def scan(self, *, count: int, reward_available: bool) -> LoyaltyState:
        if reward_available:
            return LoyaltyState(
                progress_text=self.program.render_progress(self.program.reset_count),
                status=LoyaltyStatus.REWARD_REDEEMED,
                customer_message=self.program.reward_redeemed_message,
                barista_message=self.program.barista_make_free_message,
                reward_available=False,
                reset_applied=True,
            )

        next_count = min(count + 1, self.program.required_paid_coffees)
        reward_now_available = next_count >= self.program.required_paid_coffees
        return LoyaltyState(
            progress_text=self.program.render_progress(next_count),
            status=LoyaltyStatus.REWARD_READY if reward_now_available else LoyaltyStatus.COLLECTING,
            customer_message=self.program.reward_ready_message if reward_now_available else '',
            barista_message=(
                self.program.barista_reward_ready_message
                if reward_now_available
                else self.program.barista_progress_template.format(
                    count=next_count,
                    goal=self.program.required_paid_coffees,
                )
            ),
            reward_available=reward_now_available,
            reset_applied=False,
        )
