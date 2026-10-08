"""Чистые функции разбора форматов демо-банка."""

import datetime
import re
from dataclasses import dataclass
from decimal import Decimal

from src import domain

from . import selectors

CURRENCY_BY_SYMBOL = {
    '₽': 'RUB',
    '$': 'USD',
    '€': 'EUR',
}

PRODUCT_TYPE_BY_LABEL = {
    'счёт': domain.ProductType.ACCOUNT,
    'карта': domain.ProductType.CARD,
    'накопительный счёт': domain.ProductType.DEPOSIT,
    'вклад': domain.ProductType.DEPOSIT,
    'кредит': domain.ProductType.LOAN,
}

# '−1 450,00 ₽': знак, цифры с пробелами-разделителями тысяч, необязательные копейки, символ валюты
MONEY_PATTERN = re.compile(
    r'^(?P<sign>[-−]?)(?P<integer>\d{1,3}(?: \d{3})*|\d+)(?:,(?P<fraction>\d{1,2}))? (?P<symbol>\S)$'
)
PERCENT_PATTERN = re.compile(r'^(?P<number>\d+(?:,\d+)?) ?%$')
DATE_FORMAT = '%d.%m.%Y'


@dataclass
class ProductField:
    text: str
    link: str | None = None


@dataclass
class ParsedMoney:
    amount: Decimal
    currency: str


def parse_money(text: str) -> ParsedMoney:
    match = MONEY_PATTERN.match(_normalize_spaces(text))
    if not match:
        # Значение не пишем в текст ошибки: суммы не должны попадать в логи
        raise ValueError('Unknown money format')

    currency = CURRENCY_BY_SYMBOL.get(match['symbol'])
    if not currency:
        raise ValueError('Unknown currency symbol')

    number = match['integer'].replace(' ', '')
    if match['fraction']:
        number = f'{number}.{match["fraction"]}'
    amount = Decimal(number)
    if match['sign']:
        amount = -amount
    return ParsedMoney(amount=amount, currency=currency)


def parse_percent(text: str) -> Decimal:
    match = PERCENT_PATTERN.match(_normalize_spaces(text))
    if not match:
        raise ValueError(f'Unknown percent format: {text!r}')
    return Decimal(match['number'].replace(',', '.'))


def parse_date(text: str) -> datetime.date:
    return datetime.datetime.strptime(text.strip(), DATE_FORMAT).date()


def parse_product_type(text: str) -> domain.ProductType:
    product_type = PRODUCT_TYPE_BY_LABEL.get(text.strip().lower())
    if not product_type:
        raise ValueError(f'Unknown product type: {text!r}')
    return product_type


def parse_product_id(link: str) -> str:
    """'/products/acc-rub' → 'acc-rub'."""
    product_id = link.rstrip('/').rsplit('/', 1)[-1]
    if not product_id:
        raise ValueError(f'Unknown product link: {link!r}')
    return product_id


def parse_product(product_id: str, name: str, fields: dict[str, ProductField]) -> domain.Product:
    """Собирает продукт из полей его страницы; полный номер карты сразу маскируется."""
    if selectors.FIELD_TYPE not in fields:
        raise ValueError('Product type not found')
    product_type = parse_product_type(fields[selectors.FIELD_TYPE].text)

    balance = _read_money(fields, selectors.FIELD_BALANCE)
    available_balance = _read_money(fields, selectors.FIELD_AVAILABLE_BALANCE)
    credit_limit = _read_money(fields, selectors.FIELD_CREDIT_LIMIT)
    debt = _read_money(fields, selectors.FIELD_DEBT)
    money_values = [money for money in (balance, available_balance, credit_limit, debt) if money is not None]
    if not money_values:
        raise ValueError('Product currency not found')

    card_number = _read_text(fields, selectors.FIELD_CARD_NUMBER)
    account_number = _read_text(fields, selectors.FIELD_ACCOUNT_NUMBER)
    linked_account = fields.get(selectors.FIELD_LINKED_ACCOUNT)
    interest_rate = _read_text(fields, selectors.FIELD_INTEREST_RATE)
    opened_at = _read_text(fields, selectors.FIELD_OPENED_AT)

    return domain.Product(
        product_id=product_id,
        type=product_type,
        name=name.strip(),
        masked_number=domain.mask_number(card_number or account_number or ''),
        currency=money_values[0].currency,
        balance=balance.amount if balance else None,
        available_balance=available_balance.amount if available_balance else None,
        linked_account_id=parse_product_id(linked_account.link) if linked_account and linked_account.link else None,
        requisites=_read_requisites(fields, account_number),
        details=domain.ProductDetails(
            interest_rate=parse_percent(interest_rate) if interest_rate else None,
            opened_at=parse_date(opened_at) if opened_at else None,
            credit_limit=credit_limit.amount if credit_limit else None,
            debt=debt.amount if debt else None,
        ),
    )


def _read_text(fields: dict[str, ProductField], label: str) -> str | None:
    product_field = fields.get(label)
    if product_field is None:
        return None
    return product_field.text.strip() or None


def _read_money(fields: dict[str, ProductField], label: str) -> ParsedMoney | None:
    text = _read_text(fields, label)
    return parse_money(text) if text else None


def _read_requisites(fields: dict[str, ProductField], account_number: str | None) -> domain.ProductRequisites | None:
    bic = _read_text(fields, selectors.FIELD_BIC)
    correspondent_account = _read_text(fields, selectors.FIELD_CORRESPONDENT_ACCOUNT)
    bank_name = _read_text(fields, selectors.FIELD_BANK_NAME)
    if not any((account_number, bic, correspondent_account, bank_name)):
        return None
    return domain.ProductRequisites(
        account_number=account_number,
        bic=bic,
        correspondent_account=correspondent_account,
        bank_name=bank_name,
    )


def _normalize_spaces(text: str) -> str:
    """Неразрывные и повторные пробелы → один обычный пробел."""
    return ' '.join(text.replace(' ', ' ').split())
