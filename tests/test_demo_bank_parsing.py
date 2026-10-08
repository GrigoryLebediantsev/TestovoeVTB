import datetime
from decimal import Decimal

import pytest

from src import domain
from src.adapter.demo_bank import parsing

HISTORY_PERIOD = domain.Period(date_from=datetime.date(2026, 5, 1), date_to=datetime.date(2026, 6, 30))
CARD_PURCHASE_ITEM: dict[str, object] = {
    'id': 'tx-c-001',
    'operationDate': '2026-05-03',
    'postingDate': '2026-05-04',
    'amount': '-1450.00',
    'currency': 'RUB',
    'description': 'Пятёрочка',
    'counterparty': 'Пятёрочка',
    'category': 'Супермаркеты',
    'status': 'POSTED',
}
PENDING_REFUND_ITEM: dict[str, object] = {
    'id': None,
    'operationDate': '2026-06-28',
    'postingDate': None,
    'amount': '640',
    'currency': 'RUB',
    'description': 'Возврат: Кофейня',
    'counterparty': None,
    'category': 'Возврат',
    'status': 'PENDING',
}
SERVER_PORTION: dict[str, object] = {'items': [CARD_PURCHASE_ITEM, PENDING_REFUND_ITEM], 'hasMore': True}


@pytest.mark.parametrize(
    ('text', 'expected_amount', 'expected_currency'),
    [
        ('125 430,50 ₽', Decimal('125430.50'), 'RUB'),
        ('125 430,50 ₽', Decimal('125430.50'), 'RUB'),
        ('2 350,00 $', Decimal('2350.00'), 'USD'),
        ('99,90 €', Decimal('99.90'), 'EUR'),
        ('−1 450,00 ₽', Decimal('-1450.00'), 'RUB'),
        ('-0,01 ₽', Decimal('-0.01'), 'RUB'),
        ('+50 000,00 ₽', Decimal('50000.00'), 'RUB'),
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


@pytest.mark.parametrize(('text', 'expected'), [('01.05.2026', datetime.date(2026, 5, 1)), ('—', None), ('', None)])
def test_parse_optional_date(text: str, expected: datetime.date | None) -> None:
    assert parsing.parse_optional_date(text) == expected


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Проведена', domain.TransactionStatus.POSTED),
        ('В обработке', domain.TransactionStatus.PENDING),
        ('Отклонена', domain.TransactionStatus.DECLINED),
        (' проведена ', domain.TransactionStatus.POSTED),
    ],
)
def test_parse_transaction_status(text: str, expected: domain.TransactionStatus) -> None:
    assert parsing.parse_transaction_status(text) == expected


def test_parse_transaction_status_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        parsing.parse_transaction_status('Заморожена')


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Пополнение', domain.TransactionCategory.TOP_UP),
        ('Проценты', domain.TransactionCategory.INTEREST),
        ('Снятие', domain.TransactionCategory.WITHDRAWAL),
        ('Перевод', domain.TransactionCategory.TRANSFER),
        (' перевод ', domain.TransactionCategory.TRANSFER),
        ('Зарплата', domain.TransactionCategory.SALARY),
        ('Супермаркеты', domain.TransactionCategory.GROCERIES),
        ('Рестораны', domain.TransactionCategory.RESTAURANTS),
        ('Транспорт', domain.TransactionCategory.TRANSPORT),
        ('Покупки', domain.TransactionCategory.SHOPPING),
        ('Возврат', domain.TransactionCategory.REFUND),
        ('Коммунальные платежи', domain.TransactionCategory.UTILITIES),
        ('Комиссия', domain.TransactionCategory.FEE),
        ('Кешбэк за покупки', domain.TransactionCategory.OTHER),
        ('', domain.TransactionCategory.OTHER),
    ],
)
def test_parse_transaction_category(text: str, expected: domain.TransactionCategory) -> None:
    assert parsing.parse_transaction_category(text) == expected


def make_row(
    bank_id: str | None = None,
    amount: str = '+1 000,00 ₽',
    counterparty: str = 'Текущий счёт •• 4567',
) -> parsing.TransactionRow:
    return parsing.TransactionRow(
        bank_id=bank_id,
        operation_date='20.05.2026',
        posting_date='20.05.2026',
        description='Пополнение с текущего счёта',
        counterparty=counterparty,
        category='Пополнение',
        status='Проведена',
        amount=amount,
    )


def test_parse_transactions_normalizes_row_with_bank_id() -> None:
    [transaction] = parsing.parse_transactions('savings', [make_row(bank_id='sv-0002', amount='−20 000,00 ₽')])

    assert transaction == domain.Transaction(
        transaction_id='sv-0002',
        id_source=domain.TransactionIdSource.BANK,
        product_id='savings',
        operation_date=datetime.date(2026, 5, 20),
        posting_date=datetime.date(2026, 5, 20),
        amount=Decimal('-20000.00'),
        currency='RUB',
        type=domain.TransactionType.DEBIT,
        description='Пополнение с текущего счёта',
        counterparty='Текущий счёт •• 4567',
        category=domain.TransactionCategory.TOP_UP,
        status=domain.TransactionStatus.POSTED,
    )


def test_parse_transactions_generates_ids_when_bank_gives_none() -> None:
    first, second = parsing.parse_transactions('savings', [make_row(), make_row()])

    assert first.id_source == domain.TransactionIdSource.GENERATED
    assert second.id_source == domain.TransactionIdSource.GENERATED
    assert first.transaction_id.endswith('-1')
    assert second.transaction_id.endswith('-2')
    assert first.type == domain.TransactionType.CREDIT


def test_parse_transactions_treats_dash_as_missing_counterparty() -> None:
    [transaction] = parsing.parse_transactions('savings', [make_row(counterparty='—')])

    assert transaction.counterparty is None


def test_generated_id_survives_posting_of_pending_operation() -> None:
    pending_row = make_row()
    pending_row.posting_date = '—'
    pending_row.status = 'В обработке'
    posted_row = make_row()

    [pending] = parsing.parse_transactions('savings', [pending_row])
    [posted] = parsing.parse_transactions('savings', [posted_row])

    assert pending.transaction_id == posted.transaction_id


def test_parse_server_portion_reads_items_and_has_more() -> None:
    portion = parsing.parse_server_portion(SERVER_PORTION)

    assert portion.has_more is True
    assert len(portion.items) == 2


def test_parse_server_transactions_normalizes_items() -> None:
    portion = parsing.parse_server_portion(SERVER_PORTION)

    with_bank_id, without_bank_id = parsing.parse_server_transactions('card-debit', portion.items)

    assert with_bank_id == domain.Transaction(
        transaction_id='tx-c-001',
        id_source=domain.TransactionIdSource.BANK,
        product_id='card-debit',
        operation_date=datetime.date(2026, 5, 3),
        posting_date=datetime.date(2026, 5, 4),
        amount=Decimal('-1450.00'),
        currency='RUB',
        type=domain.TransactionType.DEBIT,
        description='Пятёрочка',
        counterparty='Пятёрочка',
        category=domain.TransactionCategory.GROCERIES,
        status=domain.TransactionStatus.POSTED,
    )
    assert without_bank_id.id_source == domain.TransactionIdSource.GENERATED
    assert without_bank_id.transaction_id.endswith('-1')
    assert without_bank_id.posting_date is None
    assert without_bank_id.amount == Decimal('640')
    assert without_bank_id.type == domain.TransactionType.CREDIT
    assert without_bank_id.category == domain.TransactionCategory.REFUND
    assert without_bank_id.status == domain.TransactionStatus.PENDING


def test_server_and_page_give_same_generated_id_for_same_operation() -> None:
    server_item = parsing.parse_server_portion(SERVER_PORTION).items[1]
    page_row = parsing.TransactionRow(
        bank_id=None,
        operation_date='28.06.2026',
        posting_date='—',
        description='Возврат: Кофейня',
        counterparty='—',
        category='Возврат',
        status='В обработке',
        amount='+640,00 ₽',
    )

    [from_server] = parsing.parse_server_transactions('card-debit', [server_item])
    [from_page] = parsing.parse_transactions('card-debit', [page_row])

    assert from_server == from_page


@pytest.mark.parametrize(
    ('code', 'expected'),
    [
        ('POSTED', domain.TransactionStatus.POSTED),
        ('PENDING', domain.TransactionStatus.PENDING),
        ('DECLINED', domain.TransactionStatus.DECLINED),
    ],
)
def test_parse_server_status(code: str, expected: domain.TransactionStatus) -> None:
    assert parsing.parse_server_status(code) == expected


def test_parse_server_status_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        parsing.parse_server_status('FROZEN')


@pytest.mark.parametrize(
    'broken_item',
    [
        {'operationDate': '03.05.2026'},
        {'amount': '−1 450,00 ₽'},
        {'currency': 'рубли'},
    ],
)
def test_parse_server_portion_rejects_unknown_format(broken_item: dict[str, object]) -> None:
    portion = {'items': [CARD_PURCHASE_ITEM | broken_item], 'hasMore': False}

    with pytest.raises(ValueError):
        parsing.parse_server_portion(portion)


@pytest.mark.parametrize(
    ('url', 'period', 'expected'),
    [
        (
            'http://bank/api/products/card-debit/transactions?offset=5&from=2026-05-01&to=2026-06-30',
            HISTORY_PERIOD,
            True,
        ),
        ('http://bank/api/products/card-debit/transactions?offset=0', HISTORY_PERIOD, False),
        ('http://bank/api/products/card-debit/transactions?offset=0', None, True),
        ('http://bank/api/products/acc-usd/transactions?from=2026-05-01&to=2026-06-30', HISTORY_PERIOD, False),
        ('http://bank/products/card-debit?from=2026-05-01&to=2026-06-30', HISTORY_PERIOD, False),
    ],
)
def test_is_history_response_url(url: str, period: domain.Period | None, expected: bool) -> None:
    assert parsing.is_history_response_url(url, 'card-debit', period) == expected


EXPORT_HEADER = 'Дата операции;Дата проведения;Описание;Контрагент;Категория;Статус;Сумма;Валюта'
EXPORT_PURCHASE_LINE = (
    '03.05.2026;04.05.2026;Покупка по карте •• 9012: Пятёрочка;Пятёрочка;Супермаркеты;Проведена;-1450,00;RUB'
)


def build_export_file(*lines: str) -> bytes:
    """Файл экспорта, как его отдаёт кабинет: UTF-8 с BOM, строки через CRLF."""
    return ('﻿' + '\r\n'.join([EXPORT_HEADER, *lines]) + '\r\n').encode('utf-8')


def test_parse_export_transactions_normalizes_rows() -> None:
    [transaction] = parsing.parse_export_transactions('acc-rub', build_export_file(EXPORT_PURCHASE_LINE))

    assert transaction == domain.Transaction(
        transaction_id=transaction.transaction_id,
        id_source=domain.TransactionIdSource.GENERATED,
        product_id='acc-rub',
        operation_date=datetime.date(2026, 5, 3),
        posting_date=datetime.date(2026, 5, 4),
        amount=Decimal('-1450.00'),
        currency='RUB',
        type=domain.TransactionType.DEBIT,
        description='Покупка по карте •• 9012: Пятёрочка',
        counterparty='Пятёрочка',
        category=domain.TransactionCategory.GROCERIES,
        status=domain.TransactionStatus.POSTED,
    )


def test_export_and_page_give_same_generated_id_for_same_operation() -> None:
    page_row = parsing.TransactionRow(
        bank_id=None,
        operation_date='03.05.2026',
        posting_date='04.05.2026',
        description='Покупка по карте •• 9012: Пятёрочка',
        counterparty='Пятёрочка',
        category='Супермаркеты',
        status='Проведена',
        amount='−1 450,00 ₽',
    )

    [from_export] = parsing.parse_export_transactions('acc-rub', build_export_file(EXPORT_PURCHASE_LINE))
    [from_page] = parsing.parse_transactions('acc-rub', [page_row])

    assert from_export == from_page


@pytest.mark.parametrize(
    'content',
    [
        b'',
        'Дата;Сумма\r\n03.05.2026;-1450,00\r\n'.encode(),
        build_export_file('03.05.2026;04.05.2026;Пятёрочка;Пятёрочка;Супермаркеты;Проведена'),
        build_export_file(EXPORT_PURCHASE_LINE.replace('-1450,00', '−1 450,00 ₽')),
        build_export_file(EXPORT_PURCHASE_LINE.replace(';RUB', ';₽')),
        '\r\n'.join([EXPORT_HEADER, EXPORT_PURCHASE_LINE]).encode('cp1251'),
        # Поле длиннее предела модуля csv
        build_export_file(EXPORT_PURCHASE_LINE.replace('Пятёрочка;', 'Я' * 200_000 + ';', 1)),
    ],
    ids=['empty', 'unknown columns', 'short row', 'page amount format', 'currency symbol', 'not utf-8', 'huge field'],
)
def test_parse_export_transactions_rejects_unknown_format(content: bytes) -> None:
    with pytest.raises(ValueError):
        parsing.parse_export_transactions('acc-rub', content)


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('-1450,00', Decimal('-1450.00')),
        ('85000,00', Decimal('85000.00')),
        ('0,5', Decimal('0.5')),
        ('100', Decimal('100')),
    ],
)
def test_parse_export_amount(text: str, expected: Decimal) -> None:
    assert parsing.parse_export_amount(text) == expected
