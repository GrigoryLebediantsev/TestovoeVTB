import datetime
from dataclasses import dataclass

from .period import Period

# Что прототип прочитает в кабинете — показывается клиенту и пишется в отчёт
CONSENT_SCOPE = [
    'Список продуктов: счета, карты, накопительные счета, кредиты',
    'Остатки и доступные суммы',
    'Реквизиты счетов',
    'Ставки, даты открытия, кредитные лимиты и остаток долга',
    'Операции за выбранный период',
]


@dataclass
class Consent:
    bank_name: str
    period: Period
    scope: list[str]
    granted_at: datetime.datetime
