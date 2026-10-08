"""Данные демо-клиента: пять продуктов и их операции."""

import datetime
from dataclasses import dataclass, field
from decimal import Decimal

CLIENT_FULL_NAME = 'Иванов Иван Иванович'

BANK_NAME = 'АО «Демо-банк»'
BANK_BIC = '044525999'
BANK_CORRESPONDENT_ACCOUNT = '30101810400000000999'


@dataclass
class DemoTransaction:
    bank_id: str | None  # у части операций банк не показывает идентификатор
    operation_date: datetime.date
    posting_date: datetime.date | None
    amount: Decimal
    description: str
    counterparty: str | None
    category: str
    status: str


@dataclass
class DemoProduct:
    product_id: str
    type_label: str
    name: str
    currency: str
    opened_at: datetime.date
    account_number: str | None = None
    card_number: str | None = None
    balance: Decimal | None = None
    available_balance: Decimal | None = None
    linked_product_id: str | None = None
    interest_rate: Decimal | None = None
    credit_limit: Decimal | None = None
    debt: Decimal | None = None
    transactions: list[DemoTransaction] = field(default_factory=list)


# Период по умолчанию в .env — май–июнь 2026. Кабинет фильтрует по дате проведения, поэтому операция 30.04,
# проведённая 01.05, попадает в выдачу, хотя совершена до периода.
SAVINGS_TRANSACTIONS = [
    DemoTransaction(
        bank_id='sv-0001',
        operation_date=datetime.date(2026, 3, 15),
        posting_date=datetime.date(2026, 3, 15),
        amount=Decimal('100000.00'),
        description='Пополнение с текущего счёта',
        counterparty='Текущий счёт •• 4567',
        category='Пополнение',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 4, 30),
        posting_date=datetime.date(2026, 5, 1),
        amount=Decimal('6712.33'),
        description='Выплата процентов за апрель',
        counterparty=None,
        category='Проценты',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='sv-0002',
        operation_date=datetime.date(2026, 5, 5),
        posting_date=datetime.date(2026, 5, 5),
        amount=Decimal('50000.00'),
        description='Пополнение с текущего счёта',
        counterparty='Текущий счёт •• 4567',
        category='Пополнение',
        status='Проведена',
    ),
    # Две одинаковые операции без идентификатора банка
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 20),
        posting_date=datetime.date(2026, 5, 20),
        amount=Decimal('1000.00'),
        description='Пополнение через СБП',
        counterparty='Пётр С.',
        category='Пополнение',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 20),
        posting_date=datetime.date(2026, 5, 20),
        amount=Decimal('1000.00'),
        description='Пополнение через СБП',
        counterparty='Пётр С.',
        category='Пополнение',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 31),
        posting_date=datetime.date(2026, 5, 31),
        amount=Decimal('6890.41'),
        description='Выплата процентов за май',
        counterparty=None,
        category='Проценты',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='sv-0003',
        operation_date=datetime.date(2026, 6, 10),
        posting_date=datetime.date(2026, 6, 10),
        amount=Decimal('-20000.00'),
        description='Перевод на текущий счёт',
        counterparty='Текущий счёт •• 4567',
        category='Снятие',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='sv-0004',
        operation_date=datetime.date(2026, 6, 15),
        posting_date=None,
        amount=Decimal('-5000.00'),
        description='Перевод в другой банк',
        counterparty='ООО «Ромашка»',
        category='Перевод',
        status='Отклонена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 6, 30),
        posting_date=None,
        amount=Decimal('7012.05'),
        description='Выплата процентов за июнь',
        counterparty=None,
        category='Проценты',
        status='В обработке',
    ),
]

PRODUCTS = [
    DemoProduct(
        product_id='acc-rub',
        type_label='Счёт',
        name='Текущий счёт',
        currency='RUB',
        opened_at=datetime.date(2021, 3, 15),
        account_number='40817810500001234567',
        balance=Decimal('125430.50'),
        available_balance=Decimal('125430.50'),
    ),
    DemoProduct(
        product_id='acc-usd',
        type_label='Счёт',
        name='Счёт в долларах',
        currency='USD',
        opened_at=datetime.date(2022, 7, 1),
        account_number='40817840500007654321',
        balance=Decimal('2350.00'),
        available_balance=Decimal('2350.00'),
    ),
    DemoProduct(
        product_id='card-debit',
        type_label='Карта',
        name='Дебетовая карта',
        currency='RUB',
        opened_at=datetime.date(2021, 3, 20),
        card_number='2200701234569012',
        balance=Decimal('125430.50'),
        available_balance=Decimal('120430.50'),
        linked_product_id='acc-rub',
    ),
    DemoProduct(
        product_id='savings',
        type_label='Накопительный счёт',
        name='Накопительный счёт',
        currency='RUB',
        opened_at=datetime.date(2024, 1, 10),
        account_number='40817810900005551234',
        balance=Decimal('500000.00'),
        available_balance=Decimal('500000.00'),
        interest_rate=Decimal('16.5'),
        transactions=SAVINGS_TRANSACTIONS,
    ),
    DemoProduct(
        product_id='loan',
        type_label='Кредит',
        name='Потребительский кредит',
        currency='RUB',
        opened_at=datetime.date(2025, 2, 1),
        account_number='45507810300004443322',
        interest_rate=Decimal('21.9'),
        debt=Decimal('230000.00'),
    ),
]

PRODUCTS_BY_ID = {product.product_id: product for product in PRODUCTS}
