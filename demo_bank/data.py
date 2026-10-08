"""Данные демо-клиента: пять продуктов."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

CLIENT_FULL_NAME = 'Иванов Иван Иванович'

BANK_NAME = 'АО «Демо-банк»'
BANK_BIC = '044525999'
BANK_CORRESPONDENT_ACCOUNT = '30101810400000000999'


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
