"""Как кабинет демо-банка показывает даты, суммы и статусы: обычный формат или изменённый (режим changed_format)."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from .data import DemoTransaction

CURRENCY_SYMBOLS = {'RUB': '₽', 'USD': '$', 'EUR': '€'}
MONTH_NAMES_GENITIVE = [
    'января',
    'февраля',
    'марта',
    'апреля',
    'мая',
    'июня',
    'июля',
    'августа',
    'сентября',
    'октября',
    'ноября',
    'декабря',
]
NUMERIC_DATE_FORMAT = '%d.%m.%Y'
NON_BREAKING_SPACE = '\u00a0'
# В изменённом формате банк переименовал статус одной операции — прототип его не знает
CHANGED_STATUS_BY_BANK_ID = {'sv-0003': 'Исполнена'}


@dataclass(frozen=True)
class ValueFormat:
    is_changed: bool = False

    def money(self, amount: Decimal, currency: str, show_plus: bool = False) -> str:
        """Обычный: '−125 430,50 ₽' (пробелы неразрывные). Изменённый: '-125430.50 RUB'."""
        if self.is_changed:
            return f'{amount:.2f} {currency}'
        sign = '−' if amount < 0 else ''
        if show_plus and amount > 0:
            sign = '+'
        integer_part, fraction_part = f'{abs(amount):.2f}'.split('.')
        grouped = f'{int(integer_part):,}'.replace(',', NON_BREAKING_SPACE)
        return f'{sign}{grouped},{fraction_part}{NON_BREAKING_SPACE}{CURRENCY_SYMBOLS[currency]}'

    def date(self, value: datetime.date) -> str:
        """Обычный: '10.06.2026'. Изменённый: '10 июня 2026'."""
        if self.is_changed:
            return f'{value.day} {MONTH_NAMES_GENITIVE[value.month - 1]} {value.year}'
        return value.strftime(NUMERIC_DATE_FORMAT)

    def export_amount(self, amount: Decimal) -> str:
        """Сумма в файле экспорта: обычный '-1450,00', изменённый '-1450.00'."""
        if self.is_changed:
            return f'{amount:.2f}'
        return f'{amount:.2f}'.replace('.', ',')

    def status(self, transaction: DemoTransaction) -> str:
        if self.is_changed:
            return CHANGED_STATUS_BY_BANK_ID.get(transaction.bank_id or '', transaction.status)
        return transaction.status
