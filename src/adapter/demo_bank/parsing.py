"""Чистые функции разбора форматов демо-банка."""

import csv
import datetime
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pydantic
from pydantic.alias_generators import to_camel

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

TRANSACTION_STATUS_BY_LABEL = {
    'проведена': domain.TransactionStatus.POSTED,
    'в обработке': domain.TransactionStatus.PENDING,
    'отклонена': domain.TransactionStatus.DECLINED,
}

TRANSACTION_CATEGORY_BY_LABEL = {
    'пополнение': domain.TransactionCategory.TOP_UP,
    'проценты': domain.TransactionCategory.INTEREST,
    'снятие': domain.TransactionCategory.WITHDRAWAL,
    'перевод': domain.TransactionCategory.TRANSFER,
    'зарплата': domain.TransactionCategory.SALARY,
    'супермаркеты': domain.TransactionCategory.GROCERIES,
    'рестораны': domain.TransactionCategory.RESTAURANTS,
    'транспорт': domain.TransactionCategory.TRANSPORT,
    'покупки': domain.TransactionCategory.SHOPPING,
    'возврат': domain.TransactionCategory.REFUND,
    'коммунальные платежи': domain.TransactionCategory.UTILITIES,
    'комиссия': domain.TransactionCategory.FEE,
}

# В ответах сервера статус — код, а не подпись
TRANSACTION_STATUS_BY_SERVER_CODE = {
    'POSTED': domain.TransactionStatus.POSTED,
    'PENDING': domain.TransactionStatus.PENDING,
    'DECLINED': domain.TransactionStatus.DECLINED,
}

# Так кабинет показывает пустую ячейку
EMPTY_CELL_TEXT = '—'

# '−1 450,00 ₽', '+500,00 ₽': знак, цифры с пробелами-разделителями тысяч, необязательные копейки, символ валюты
MONEY_PATTERN = re.compile(
    r'^(?P<sign>[-−+]?)(?P<integer>\d{1,3}(?: \d{3})*|\d+)(?:,(?P<fraction>\d{1,2}))? (?P<symbol>\S)$'
)
MINUS_SIGNS = ('-', '−')
PERCENT_PATTERN = re.compile(r'^(?P<number>\d+(?:,\d+)?) ?%$')
DATE_FORMAT = '%d.%m.%Y'
# Сумма в экспорте: '-1450,00' — без разделителей тысяч и символа валюты, валюта отдельной колонкой
EXPORT_AMOUNT_PATTERN = re.compile(r'^(?P<sign>-?)(?P<integer>\d+)(?:,(?P<fraction>\d{1,2}))?$')
CURRENCY_CODE_PATTERN = re.compile(r'^[A-Z]{3}$')
EXPORT_COLUMNS = [
    selectors.EXPORT_COLUMN_OPERATION_DATE,
    selectors.EXPORT_COLUMN_POSTING_DATE,
    selectors.EXPORT_COLUMN_DESCRIPTION,
    selectors.EXPORT_COLUMN_COUNTERPARTY,
    selectors.EXPORT_COLUMN_CATEGORY,
    selectors.EXPORT_COLUMN_STATUS,
    selectors.EXPORT_COLUMN_AMOUNT,
    selectors.EXPORT_COLUMN_CURRENCY,
]


@dataclass
class ProductField:
    text: str
    link: str | None = None


@dataclass
class TransactionRow:
    """Строка таблицы операций как текст ячеек."""

    bank_id: str | None
    operation_date: str
    posting_date: str
    description: str
    counterparty: str
    category: str
    status: str
    amount: str


class FetchedTransaction(pydantic.BaseModel):
    """Операция в ответе сервера банка: даты ISO, сумма строкой с точкой, код валюты."""

    model_config = pydantic.ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None
    operation_date: datetime.date
    posting_date: datetime.date | None
    amount: Decimal
    currency: str = pydantic.Field(pattern=r'^[A-Z]{3}$')
    description: str
    counterparty: str | None
    category: str
    status: str


class FetchTransactionsResponse(pydantic.BaseModel):
    """Порция истории, которую страница получает от сервера банка."""

    model_config = pydantic.ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[FetchedTransaction]
    has_more: bool


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
    if match['sign'] in MINUS_SIGNS:
        amount = -amount
    return ParsedMoney(amount=amount, currency=currency)


def parse_percent(text: str) -> Decimal:
    match = PERCENT_PATTERN.match(_normalize_spaces(text))
    if not match:
        raise ValueError(f'Unknown percent format: {text!r}')
    return Decimal(match['number'].replace(',', '.'))


def parse_date(text: str) -> datetime.date:
    return datetime.datetime.strptime(text.strip(), DATE_FORMAT).date()


def parse_optional_date(text: str) -> datetime.date | None:
    if _is_empty_cell(text):
        return None
    return parse_date(text)


def parse_transaction_status(text: str) -> domain.TransactionStatus:
    status = TRANSACTION_STATUS_BY_LABEL.get(text.strip().lower())
    if not status:
        raise ValueError(f'Unknown transaction status: {text!r}')
    return status


def parse_transaction_category(text: str) -> domain.TransactionCategory:
    return TRANSACTION_CATEGORY_BY_LABEL.get(text.strip().lower(), domain.TransactionCategory.OTHER)


def parse_server_status(code: str) -> domain.TransactionStatus:
    status = TRANSACTION_STATUS_BY_SERVER_CODE.get(code.strip().upper())
    if not status:
        raise ValueError(f'Unknown transaction status code: {code!r}')
    return status


def is_history_response_url(url: str, product_id: str, period: domain.Period | None) -> bool:
    """Ответ сервера с порцией истории продукта; если период задан — только за этот период."""
    parsed_url = urlparse(url)
    if parsed_url.path != selectors.HISTORY_API_PATH.format(product_id=product_id):
        return False
    if period is None:
        return True
    query = parse_qs(parsed_url.query)
    date_from = query.get(selectors.HISTORY_API_FROM_PARAM, [''])[0]
    date_to = query.get(selectors.HISTORY_API_TO_PARAM, [''])[0]
    return date_from == period.date_from.isoformat() and date_to == period.date_to.isoformat()


def parse_server_portion(data: object) -> FetchTransactionsResponse:
    """Проверяет формат ответа сервера; незнакомый формат — ValueError."""
    return FetchTransactionsResponse.model_validate(data)


def parse_server_transactions(product_id: str, items: list[FetchedTransaction]) -> list[domain.Transaction]:
    """Приводит операции из ответов сервера к единой схеме; items — все порции истории продукта по порядку."""
    id_generator = domain.TransactionIdGenerator()
    return [_parse_server_transaction(product_id, item, id_generator) for item in items]


def parse_transactions(product_id: str, rows: list[TransactionRow]) -> list[domain.Transaction]:
    """Приводит строки таблицы к единой схеме; операциям без банковского идентификатора генерирует устойчивый."""
    id_generator = domain.TransactionIdGenerator()
    return [_parse_transaction(product_id, row, id_generator) for row in rows]


def parse_export_amount(text: str) -> Decimal:
    match = EXPORT_AMOUNT_PATTERN.match(text.strip())
    if not match:
        raise ValueError('Unknown export amount format')
    number = match['integer']
    if match['fraction']:
        number = f'{number}.{match["fraction"]}'
    amount = Decimal(number)
    return -amount if match['sign'] else amount


def parse_export_transactions(product_id: str, content: bytes) -> list[domain.Transaction]:
    """Приводит файл экспорта CSV к единой схеме; у операций в экспорте нет банковского идентификатора.

    Незнакомый формат файла — ValueError: адаптер тогда переходит к следующему способу извлечения.
    """
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), delimiter=selectors.EXPORT_DELIMITER)
    try:
        if reader.fieldnames is None or not set(EXPORT_COLUMNS) <= set(reader.fieldnames):
            raise ValueError('Unknown export columns')
        id_generator = domain.TransactionIdGenerator()
        return [_parse_export_row(product_id, row, id_generator) for row in reader]
    except csv.Error as error:
        raise ValueError('Broken export file') from error


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


def _parse_transaction(
    product_id: str, row: TransactionRow, id_generator: domain.TransactionIdGenerator
) -> domain.Transaction:
    operation_date = parse_date(row.operation_date)
    posting_date = parse_optional_date(row.posting_date)
    money = parse_money(row.amount)
    description = _normalize_spaces(row.description)

    if row.bank_id:
        transaction_id = row.bank_id
        id_source = domain.TransactionIdSource.BANK
    else:
        transaction_id = id_generator.next_id(product_id, operation_date, money.amount, description)
        id_source = domain.TransactionIdSource.GENERATED

    return domain.Transaction(
        transaction_id=transaction_id,
        id_source=id_source,
        product_id=product_id,
        operation_date=operation_date,
        posting_date=posting_date,
        amount=money.amount,
        currency=money.currency,
        type=domain.transaction_type_for_amount(money.amount),
        description=description,
        counterparty=None if _is_empty_cell(row.counterparty) else _normalize_spaces(row.counterparty),
        category=parse_transaction_category(row.category),
        status=parse_transaction_status(row.status),
    )


def _parse_server_transaction(
    product_id: str, item: FetchedTransaction, id_generator: domain.TransactionIdGenerator
) -> domain.Transaction:
    description = _normalize_spaces(item.description)
    if item.id:
        transaction_id = item.id
        id_source = domain.TransactionIdSource.BANK
    else:
        transaction_id = id_generator.next_id(product_id, item.operation_date, item.amount, description)
        id_source = domain.TransactionIdSource.GENERATED

    return domain.Transaction(
        transaction_id=transaction_id,
        id_source=id_source,
        product_id=product_id,
        operation_date=item.operation_date,
        posting_date=item.posting_date,
        amount=item.amount,
        currency=item.currency,
        type=domain.transaction_type_for_amount(item.amount),
        description=description,
        counterparty=_normalize_spaces(item.counterparty) if item.counterparty else None,
        category=parse_transaction_category(item.category),
        status=parse_server_status(item.status),
    )


def _parse_export_row(
    product_id: str, row: dict[str, str], id_generator: domain.TransactionIdGenerator
) -> domain.Transaction:
    # Короткой строке DictReader подставляет None вместо недостающих ячеек
    if any(row.get(column) is None for column in EXPORT_COLUMNS):
        raise ValueError('Export row is shorter than header')
    currency = row[selectors.EXPORT_COLUMN_CURRENCY].strip()
    if not CURRENCY_CODE_PATTERN.match(currency):
        raise ValueError('Unknown export currency format')
    operation_date = parse_date(row[selectors.EXPORT_COLUMN_OPERATION_DATE])
    amount = parse_export_amount(row[selectors.EXPORT_COLUMN_AMOUNT])
    description = _normalize_spaces(row[selectors.EXPORT_COLUMN_DESCRIPTION])
    counterparty = row[selectors.EXPORT_COLUMN_COUNTERPARTY]
    return domain.Transaction(
        transaction_id=id_generator.next_id(product_id, operation_date, amount, description),
        id_source=domain.TransactionIdSource.GENERATED,
        product_id=product_id,
        operation_date=operation_date,
        posting_date=parse_optional_date(row[selectors.EXPORT_COLUMN_POSTING_DATE]),
        amount=amount,
        currency=currency,
        type=domain.transaction_type_for_amount(amount),
        description=description,
        counterparty=None if _is_empty_cell(counterparty) else _normalize_spaces(counterparty),
        category=parse_transaction_category(row[selectors.EXPORT_COLUMN_CATEGORY]),
        status=parse_transaction_status(row[selectors.EXPORT_COLUMN_STATUS]),
    )


def _is_empty_cell(text: str) -> bool:
    return text.strip() in ('', EMPTY_CELL_TEXT)


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
