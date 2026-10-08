import datetime
from decimal import Decimal

from src import domain

CARD = domain.Product(
    product_id='card-debit',
    type=domain.ProductType.CARD,
    name='Дебетовая карта',
    masked_number='**** 9012',
    currency='RUB',
    linked_account_id='acc-rub',
)
ACCOUNT = domain.Product(
    product_id='acc-rub',
    type=domain.ProductType.ACCOUNT,
    name='Текущий счёт',
    masked_number='**** 4567',
    currency='RUB',
)
OTHER_ACCOUNT = domain.Product(
    product_id='acc-usd', type=domain.ProductType.ACCOUNT, name='Счёт USD', masked_number='**** 4321', currency='RUB'
)


def make_transaction(
    product_id: str,
    transaction_id: str,
    operation_date: datetime.date = datetime.date(2026, 5, 3),
    amount: str = '-1450.00',
    currency: str = 'RUB',
    description: str = 'Пятёрочка',
) -> domain.Transaction:
    return domain.Transaction(
        transaction_id=transaction_id,
        id_source=domain.TransactionIdSource.BANK,
        product_id=product_id,
        operation_date=operation_date,
        posting_date=operation_date,
        amount=Decimal(amount),
        currency=currency,
        type=domain.TransactionType.DEBIT,
        description=description,
        counterparty=None,
        category=domain.TransactionCategory.GROCERIES,
        status=domain.TransactionStatus.POSTED,
    )


def test_card_operation_seen_on_linked_account_is_duplicate() -> None:
    card_purchase = make_transaction('card-debit', 'card-1', description='Пятёрочка')
    account_copy = make_transaction('acc-rub', 'acc-1', description='Покупка по карте •• 9012: Пятёрочка')

    pairs = domain.find_card_duplicates([CARD, ACCOUNT], [account_copy, card_purchase])

    assert pairs == [domain.DuplicatePair(card_transaction=card_purchase, account_transaction=account_copy)]


def test_operations_differing_in_date_amount_or_currency_are_not_duplicates() -> None:
    card_purchase = make_transaction('card-debit', 'card-1')
    account_operations = [
        make_transaction('acc-rub', 'other-date', operation_date=datetime.date(2026, 5, 4)),
        make_transaction('acc-rub', 'other-amount', amount='-1451.00'),
        make_transaction('acc-rub', 'other-currency', currency='USD'),
    ]

    assert domain.find_card_duplicates([CARD, ACCOUNT], [card_purchase, *account_operations]) == []


def test_operations_of_not_linked_account_are_not_duplicates() -> None:
    card_purchase = make_transaction('card-debit', 'card-1')
    other_account_operation = make_transaction('acc-usd', 'usd-1')

    assert domain.find_card_duplicates([CARD, ACCOUNT, OTHER_ACCOUNT], [card_purchase, other_account_operation]) == []


def test_each_account_operation_matches_only_one_card_operation() -> None:
    first_ride = make_transaction('card-debit', 'card-1', amount='-63.00')
    second_ride = make_transaction('card-debit', 'card-2', amount='-63.00')
    account_copy = make_transaction('acc-rub', 'acc-1', amount='-63.00')

    pairs = domain.find_card_duplicates([CARD, ACCOUNT], [first_ride, second_ride, account_copy])

    assert pairs == [domain.DuplicatePair(card_transaction=first_ride, account_transaction=account_copy)]


def test_card_without_linked_account_has_no_duplicates() -> None:
    unlinked_card = domain.Product(
        product_id='card-debit', type=domain.ProductType.CARD, name='Карта', masked_number='**** 9012', currency='RUB'
    )
    card_purchase = make_transaction('card-debit', 'card-1')
    account_operation = make_transaction('acc-rub', 'acc-1')

    assert domain.find_card_duplicates([unlinked_card, ACCOUNT], [card_purchase, account_operation]) == []


def test_declined_operations_are_not_compared() -> None:
    declined_card_purchase = make_transaction('card-debit', 'card-1')
    declined_card_purchase.status = domain.TransactionStatus.DECLINED
    account_operation = make_transaction('acc-rub', 'acc-1')
    card_purchase = make_transaction('card-debit', 'card-2', amount='-500.00')
    declined_account_operation = make_transaction('acc-rub', 'acc-2', amount='-500.00')
    declined_account_operation.status = domain.TransactionStatus.DECLINED

    transactions = [declined_card_purchase, account_operation, card_purchase, declined_account_operation]

    assert domain.find_card_duplicates([CARD, ACCOUNT], transactions) == []


def test_pending_card_operation_can_be_duplicate() -> None:
    pending_card_purchase = make_transaction('card-debit', 'card-1')
    pending_card_purchase.status = domain.TransactionStatus.PENDING
    account_copy = make_transaction('acc-rub', 'acc-1')

    pairs = domain.find_card_duplicates([CARD, ACCOUNT], [pending_card_purchase, account_copy])

    assert pairs == [domain.DuplicatePair(card_transaction=pending_card_purchase, account_transaction=account_copy)]
