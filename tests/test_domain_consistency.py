import datetime
from decimal import Decimal

from src import domain

ACCOUNT = domain.Product(
    product_id='acc-rub',
    type=domain.ProductType.ACCOUNT,
    name='Текущий счёт',
    masked_number='**** 4567',
    currency='RUB',
)
CARD = domain.Product(
    product_id='card-debit',
    type=domain.ProductType.CARD,
    name='Дебетовая карта',
    masked_number='**** 9012',
    currency='RUB',
    linked_account_id='acc-rub',
)


def make_transaction(product_id: str, transaction_id: str, currency: str = 'RUB') -> domain.Transaction:
    return domain.Transaction(
        transaction_id=transaction_id,
        id_source=domain.TransactionIdSource.BANK,
        product_id=product_id,
        operation_date=datetime.date(2026, 5, 3),
        posting_date=datetime.date(2026, 5, 3),
        amount=Decimal('-1450.00'),
        currency=currency,
        type=domain.TransactionType.DEBIT,
        description='Пятёрочка',
        counterparty=None,
        category=domain.TransactionCategory.GROCERIES,
        status=domain.TransactionStatus.POSTED,
    )


def test_consistent_statement_has_no_problems() -> None:
    transactions = [make_transaction('acc-rub', 'r-1'), make_transaction('card-debit', 'c-1')]

    problems = domain.check_statement_consistency([ACCOUNT, CARD], transactions)

    assert problems.repeated_transaction_ids == []
    assert problems.currency_mismatches == []
    assert problems.missing_linked_accounts == []
    assert problems.is_empty()


def test_repeated_transaction_id_is_found_once() -> None:
    transactions = [
        make_transaction('acc-rub', 'same-id'),
        make_transaction('card-debit', 'same-id'),
        make_transaction('acc-rub', 'same-id'),
        make_transaction('acc-rub', 'r-2'),
    ]

    problems = domain.check_statement_consistency([ACCOUNT, CARD], transactions)

    assert problems.repeated_transaction_ids == ['same-id']
    assert not problems.is_empty()


def test_transaction_currency_differs_from_product_currency() -> None:
    usd_on_rub_account = make_transaction('acc-rub', 'r-1', currency='USD')

    problems = domain.check_statement_consistency([ACCOUNT, CARD], [usd_on_rub_account])

    assert problems.currency_mismatches == [usd_on_rub_account]


def test_card_linked_to_missing_account() -> None:
    problems = domain.check_statement_consistency([CARD], [])

    assert problems.missing_linked_accounts == [CARD]
