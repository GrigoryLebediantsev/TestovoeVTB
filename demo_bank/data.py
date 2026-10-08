"""Данные демо-клиента: пять продуктов и их операции."""

import datetime
import enum
from dataclasses import dataclass, field
from decimal import Decimal

CLIENT_FULL_NAME = 'Иванов Иван Иванович'

BANK_NAME = 'АО «Демо-банк»'
BANK_BIC = '044525999'
BANK_CORRESPONDENT_ACCOUNT = '30101810400000000999'


class HistoryLoading(enum.StrEnum):
    """Как страница продукта показывает историю операций."""

    PAGE = 'page'  # вся история в разметке страницы
    SHOW_MORE = 'show_more'  # порции с сервера по кнопке «Показать ещё»
    SCROLL = 'scroll'  # порции с сервера при прокрутке вниз


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
    history_loading: HistoryLoading = HistoryLoading.PAGE


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

# Текущий счёт: вся история на странице, идентификаторов банк не показывает.
# Покупки по карте видны и здесь — это дубликаты операций карты.
CURRENT_ACCOUNT_TRANSACTIONS = [
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 4, 20),
        posting_date=datetime.date(2026, 4, 20),
        amount=Decimal('-999.00'),
        description='Покупка по карте •• 9012: Озон',
        counterparty='Озон',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 1),
        posting_date=datetime.date(2026, 5, 1),
        amount=Decimal('85000.00'),
        description='Зарплата за апрель',
        counterparty='ООО «Работа»',
        category='Зарплата',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 3),
        posting_date=datetime.date(2026, 5, 4),
        amount=Decimal('-1450.00'),
        description='Покупка по карте •• 9012: Пятёрочка',
        counterparty='Пятёрочка',
        category='Супермаркеты',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 5),
        posting_date=datetime.date(2026, 5, 5),
        amount=Decimal('-50000.00'),
        description='Перевод на накопительный счёт',
        counterparty='Накопительный счёт •• 1234',
        category='Перевод',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 12),
        posting_date=datetime.date(2026, 5, 13),
        amount=Decimal('-2300.00'),
        description='Покупка по карте •• 9012: Кофейня «Зерно»',
        counterparty='Кофейня «Зерно»',
        category='Рестораны',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 25),
        posting_date=datetime.date(2026, 5, 25),
        amount=Decimal('-63.00'),
        description='Покупка по карте •• 9012: Метро',
        counterparty='Метро',
        category='Транспорт',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 5, 30),
        posting_date=datetime.date(2026, 6, 1),
        amount=Decimal('-4999.00'),
        description='Покупка по карте •• 9012: Озон',
        counterparty='Озон',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 6, 1),
        posting_date=datetime.date(2026, 6, 1),
        amount=Decimal('85000.00'),
        description='Зарплата за май',
        counterparty='ООО «Работа»',
        category='Зарплата',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 6, 10),
        posting_date=datetime.date(2026, 6, 10),
        amount=Decimal('20000.00'),
        description='Перевод с накопительного счёта',
        counterparty='Накопительный счёт •• 1234',
        category='Пополнение',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id=None,
        operation_date=datetime.date(2026, 6, 15),
        posting_date=datetime.date(2026, 6, 15),
        amount=Decimal('-12000.00'),
        description='Оплата ЖКУ',
        counterparty='ООО «УК Дом»',
        category='Коммунальные платежи',
        status='Проведена',
    ),
]

# Счёт USD: история порциями с сервера по кнопке «Показать ещё»
USD_ACCOUNT_TRANSACTIONS = [
    DemoTransaction(
        bank_id='u-000',
        operation_date=datetime.date(2026, 4, 15),
        posting_date=datetime.date(2026, 4, 15),
        amount=Decimal('3000.00'),
        description='Входящий перевод SWIFT',
        counterparty='ACME Corp.',
        category='Перевод',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-001',
        operation_date=datetime.date(2026, 5, 2),
        posting_date=datetime.date(2026, 5, 2),
        amount=Decimal('3000.00'),
        description='Входящий перевод SWIFT',
        counterparty='ACME Corp.',
        category='Перевод',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-002',
        operation_date=datetime.date(2026, 5, 4),
        posting_date=datetime.date(2026, 5, 5),
        amount=Decimal('-45.90'),
        description='Netflix',
        counterparty='Netflix',
        category='Подписки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-003',
        operation_date=datetime.date(2026, 5, 8),
        posting_date=datetime.date(2026, 5, 9),
        amount=Decimal('-120.00'),
        description='Amazon',
        counterparty='Amazon',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-004',
        operation_date=datetime.date(2026, 5, 11),
        posting_date=datetime.date(2026, 5, 11),
        amount=Decimal('-15.00'),
        description='Комиссия за перевод',
        counterparty=None,
        category='Комиссия',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-005',
        operation_date=datetime.date(2026, 5, 15),
        posting_date=datetime.date(2026, 5, 16),
        amount=Decimal('-250.00'),
        description='Booking.com',
        counterparty='Booking.com',
        category='Путешествия',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-006',
        operation_date=datetime.date(2026, 5, 20),
        posting_date=datetime.date(2026, 5, 21),
        amount=Decimal('500.00'),
        description='Возврат: Booking.com',
        counterparty='Booking.com',
        category='Возврат',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-007',
        operation_date=datetime.date(2026, 5, 26),
        posting_date=datetime.date(2026, 5, 27),
        amount=Decimal('-89.99'),
        description='Apple',
        counterparty='Apple',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-008',
        operation_date=datetime.date(2026, 6, 2),
        posting_date=datetime.date(2026, 6, 2),
        amount=Decimal('3000.00'),
        description='Входящий перевод SWIFT',
        counterparty='ACME Corp.',
        category='Перевод',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-009',
        operation_date=datetime.date(2026, 6, 5),
        posting_date=datetime.date(2026, 6, 5),
        amount=Decimal('-45.90'),
        description='Netflix',
        counterparty='Netflix',
        category='Подписки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-010',
        operation_date=datetime.date(2026, 6, 12),
        posting_date=datetime.date(2026, 6, 13),
        amount=Decimal('-310.00'),
        description='Amazon',
        counterparty='Amazon',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-011',
        operation_date=datetime.date(2026, 6, 21),
        posting_date=datetime.date(2026, 6, 22),
        amount=Decimal('-60.00'),
        description='Uber',
        counterparty='Uber',
        category='Транспорт',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='u-012',
        operation_date=datetime.date(2026, 6, 29),
        posting_date=None,
        amount=Decimal('-199.00'),
        description='Amazon',
        counterparty='Amazon',
        category='Покупки',
        status='В обработке',
    ),
]

# Дебетовая карта: история порциями с сервера при прокрутке.
# Две одинаковые поездки в метро 25.05, а на счёте видна одна — дубликатом считается только одна.
CARD_TRANSACTIONS = [
    DemoTransaction(
        bank_id='c-000',
        operation_date=datetime.date(2026, 4, 20),
        posting_date=datetime.date(2026, 4, 20),
        amount=Decimal('-999.00'),
        description='Озон',
        counterparty='Озон',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-001',
        operation_date=datetime.date(2026, 5, 3),
        posting_date=datetime.date(2026, 5, 4),
        amount=Decimal('-1450.00'),
        description='Пятёрочка',
        counterparty='Пятёрочка',
        category='Супермаркеты',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-002',
        operation_date=datetime.date(2026, 5, 7),
        posting_date=datetime.date(2026, 5, 7),
        amount=Decimal('-389.00'),
        description='Яндекс Такси',
        counterparty='Яндекс Такси',
        category='Транспорт',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-003',
        operation_date=datetime.date(2026, 5, 12),
        posting_date=datetime.date(2026, 5, 13),
        amount=Decimal('-2300.00'),
        description='Кофейня «Зерно»',
        counterparty='Кофейня «Зерно»',
        category='Рестораны',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-004',
        operation_date=datetime.date(2026, 5, 18),
        posting_date=datetime.date(2026, 5, 18),
        amount=Decimal('1200.00'),
        description='Возврат: Озон',
        counterparty='Озон',
        category='Возврат',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-005',
        operation_date=datetime.date(2026, 5, 25),
        posting_date=datetime.date(2026, 5, 25),
        amount=Decimal('-63.00'),
        description='Метро',
        counterparty='Метро',
        category='Транспорт',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-006',
        operation_date=datetime.date(2026, 5, 25),
        posting_date=datetime.date(2026, 5, 25),
        amount=Decimal('-63.00'),
        description='Метро',
        counterparty='Метро',
        category='Транспорт',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-007',
        operation_date=datetime.date(2026, 5, 30),
        posting_date=datetime.date(2026, 6, 1),
        amount=Decimal('-4999.00'),
        description='Озон',
        counterparty='Озон',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-008',
        operation_date=datetime.date(2026, 6, 5),
        posting_date=datetime.date(2026, 6, 5),
        amount=Decimal('-780.00'),
        description='Аптека «Здоровье»',
        counterparty='Аптека «Здоровье»',
        category='Покупки',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-009',
        operation_date=datetime.date(2026, 6, 14),
        posting_date=None,
        amount=Decimal('-15000.00'),
        description='Авиабилеты',
        counterparty='Аэрофлот',
        category='Путешествия',
        status='Отклонена',
    ),
    DemoTransaction(
        bank_id='c-010',
        operation_date=datetime.date(2026, 6, 20),
        posting_date=datetime.date(2026, 6, 20),
        amount=Decimal('-1290.00'),
        description='Пятёрочка',
        counterparty='Пятёрочка',
        category='Супермаркеты',
        status='Проведена',
    ),
    DemoTransaction(
        bank_id='c-011',
        operation_date=datetime.date(2026, 6, 28),
        posting_date=None,
        amount=Decimal('-640.00'),
        description='Кофейня «Зерно»',
        counterparty='Кофейня «Зерно»',
        category='Рестораны',
        status='В обработке',
    ),
    DemoTransaction(
        bank_id='c-012',
        operation_date=datetime.date(2026, 6, 30),
        posting_date=None,
        amount=Decimal('-350.00'),
        description='Яндекс Такси',
        counterparty='Яндекс Такси',
        category='Транспорт',
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
        transactions=CURRENT_ACCOUNT_TRANSACTIONS,
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
        transactions=USD_ACCOUNT_TRANSACTIONS,
        history_loading=HistoryLoading.SHOW_MORE,
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
        transactions=CARD_TRANSACTIONS,
        history_loading=HistoryLoading.SCROLL,
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


def filter_by_posting_date(
    transactions: list[DemoTransaction], date_from: datetime.date | None, date_to: datetime.date | None
) -> list[DemoTransaction]:
    """Фильтр кабинета: по дате проведения, у непроведённых — по дате операции."""
    selected = []
    for transaction in transactions:
        filter_date = transaction.posting_date or transaction.operation_date
        if date_from and filter_date < date_from:
            continue
        if date_to and filter_date > date_to:
            continue
        selected.append(transaction)
    return selected
