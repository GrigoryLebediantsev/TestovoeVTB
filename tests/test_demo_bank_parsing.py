import datetime
from decimal import Decimal

import pytest

from src import domain
from src.adapter.demo_bank import parsing


@pytest.mark.parametrize(
    ('text', 'expected_amount', 'expected_currency'),
    [
        ('125 430,50 ₽', Decimal('125430.50'), 'RUB'),
        ('125 430,50 ₽', Decimal('125430.50'), 'RUB'),
        ('2 350,00 $', Decimal('2350.00'), 'USD'),
        ('99,90 €', Decimal('99.90'), 'EUR'),
        ('−1 450,00 ₽', Decimal('-1450.00'), 'RUB'),
        ('-0,01 ₽', Decimal('-0.01'), 'RUB'),
        ('500 000 ₽', Decimal('500000'), 'RUB'),
    ],
)
def test_parse_money_reads_amount_and_currency(text: str, expected_amount: Decimal, expected_currency: str) -> None:
    money = parsing.parse_money(text)

    assert money.amount == expected_amount
    assert money.currency == expected_currency


@pytest.mark.parametrize('text', ['', 'сто рублей', '125,50', '12,5 ¥'])
def test_parse_money_rejects_unknown_format(text: str) -> None:
    with pytest.raises(ValueError):
        parsing.parse_money(text)


@pytest.mark.parametrize(
    ('text', 'expected'),
    [('16,5 %', Decimal('16.5')), ('12%', Decimal('12')), ('0,01 %', Decimal('0.01'))],
)
def test_parse_percent(text: str, expected: Decimal) -> None:
    assert parsing.parse_percent(text) == expected


def test_parse_date_reads_russian_numeric_date() -> None:
    assert parsing.parse_date('15.03.2021') == datetime.date(2021, 3, 15)


@pytest.mark.parametrize('text', ['2021-03-15', '32.01.2021', ''])
def test_parse_date_rejects_unknown_format(text: str) -> None:
    with pytest.raises(ValueError):
        parsing.parse_date(text)


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Счёт', domain.ProductType.ACCOUNT),
        ('Карта', domain.ProductType.CARD),
        ('Накопительный счёт', domain.ProductType.DEPOSIT),
        ('Вклад', domain.ProductType.DEPOSIT),
        ('Кредит', domain.ProductType.LOAN),
        (' счёт ', domain.ProductType.ACCOUNT),
    ],
)
def test_parse_product_type(text: str, expected: domain.ProductType) -> None:
    assert parsing.parse_product_type(text) == expected


def test_parse_product_type_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        parsing.parse_product_type('Брокерский счёт')


def test_parse_product_masks_card_number_and_reads_linked_account() -> None:
    fields = {
        'Тип': parsing.ProductField(text='Карта'),
        'Номер карты': parsing.ProductField(text='2200 7012 3456 9012'),
        'Баланс': parsing.ProductField(text='125 430,50 ₽'),
        'Доступно': parsing.ProductField(text='120 430,50 ₽'),
        'Дата открытия': parsing.ProductField(text='20.03.2021'),
        'Привязанный счёт': parsing.ProductField(text='Текущий счёт •• 4567', link='/products/acc-rub'),
    }

    product = parsing.parse_product('card-debit', 'Дебетовая карта', fields)

    assert product == domain.Product(
        product_id='card-debit',
        type=domain.ProductType.CARD,
        name='Дебетовая карта',
        masked_number='**** 9012',
        currency='RUB',
        balance=Decimal('125430.50'),
        available_balance=Decimal('120430.50'),
        linked_account_id='acc-rub',
        requisites=None,
        details=domain.ProductDetails(opened_at=datetime.date(2021, 3, 20)),
    )


def test_parse_product_reads_requisites_and_loan_details() -> None:
    fields = {
        'Тип': parsing.ProductField(text='Кредит'),
        'Номер счёта': parsing.ProductField(text='45507810300004443322'),
        'Остаток долга': parsing.ProductField(text='230 000,00 ₽'),
        'Ставка': parsing.ProductField(text='21,9 %'),
        'Дата открытия': parsing.ProductField(text='01.02.2025'),
        'БИК': parsing.ProductField(text='044525999'),
        'Корр. счёт': parsing.ProductField(text='30101810400000000999'),
        'Банк получателя': parsing.ProductField(text='АО «Демо-банк»'),
    }

    product = parsing.parse_product('loan', 'Потребительский кредит', fields)

    assert product == domain.Product(
        product_id='loan',
        type=domain.ProductType.LOAN,
        name='Потребительский кредит',
        masked_number='**** 3322',
        currency='RUB',
        requisites=domain.ProductRequisites(
            account_number='45507810300004443322',
            bic='044525999',
            correspondent_account='30101810400000000999',
            bank_name='АО «Демо-банк»',
        ),
        details=domain.ProductDetails(
            interest_rate=Decimal('21.9'), opened_at=datetime.date(2025, 2, 1), debt=Decimal('230000.00')
        ),
    )


def test_parse_product_without_type_fails() -> None:
    with pytest.raises(ValueError):
        parsing.parse_product('unknown', 'Продукт', {'Баланс': parsing.ProductField(text='1,00 ₽')})
