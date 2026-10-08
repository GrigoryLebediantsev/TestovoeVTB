import datetime
from decimal import Decimal

import pytest

from src import domain

PERIOD = domain.Period(date_from=datetime.date(2026, 5, 1), date_to=datetime.date(2026, 6, 30))


def make_transaction(operation_date: datetime.date, transaction_id: str = 'bank-1') -> domain.Transaction:
    return domain.Transaction(
        transaction_id=transaction_id,
        id_source=domain.TransactionIdSource.BANK,
        product_id='savings',
        operation_date=operation_date,
        posting_date=operation_date,
        amount=Decimal('100.00'),
        currency='RUB',
        type=domain.TransactionType.CREDIT,
        description='Пополнение',
        counterparty=None,
        category=domain.TransactionCategory.TOP_UP,
        status=domain.TransactionStatus.POSTED,
    )


def test_split_by_period_keeps_bounds_and_uses_posting_date() -> None:
    first_day = make_transaction(datetime.date(2026, 5, 1), 'first-day')
    last_day = make_transaction(datetime.date(2026, 6, 30), 'last-day')
    day_before = make_transaction(datetime.date(2026, 4, 30), 'day-before')
    day_after = make_transaction(datetime.date(2026, 7, 1), 'day-after')
    # Совершена до периода, но проведена в нём — в периоде
    posted_on_first_day = make_transaction(datetime.date(2026, 4, 30), 'posted-on-first-day')
    posted_on_first_day.posting_date = datetime.date(2026, 5, 1)
    # Совершена в периоде, но проведена после него — вне периода
    posted_after_last_day = make_transaction(datetime.date(2026, 6, 30), 'posted-after-last-day')
    posted_after_last_day.posting_date = datetime.date(2026, 7, 1)

    result = domain.split_by_period(
        [day_before, posted_on_first_day, first_day, last_day, posted_after_last_day, day_after], PERIOD
    )

    assert result.inside == [posted_on_first_day, first_day, last_day]
    assert result.outside == [day_before, posted_after_last_day, day_after]


def test_split_by_period_uses_operation_date_without_posting_date() -> None:
    pending_on_last_day = make_transaction(datetime.date(2026, 6, 30), 'pending-on-last-day')
    pending_on_last_day.posting_date = None
    declined_after_period = make_transaction(datetime.date(2026, 7, 1), 'declined-after-period')
    declined_after_period.posting_date = None

    result = domain.split_by_period([pending_on_last_day, declined_after_period], PERIOD)

    assert result.inside == [pending_on_last_day]
    assert result.outside == [declined_after_period]


@pytest.mark.parametrize(
    ('amount', 'expected'),
    [(Decimal('-0.01'), domain.TransactionType.DEBIT), (Decimal('50000.00'), domain.TransactionType.CREDIT)],
)
def test_transaction_type_follows_amount_sign(amount: Decimal, expected: domain.TransactionType) -> None:
    assert domain.transaction_type_for_amount(amount) == expected


def generate_id(
    generator: domain.TransactionIdGenerator, amount: str = '1000.00', description: str = 'Пополнение'
) -> str:
    return generator.next_id(
        product_id='savings',
        operation_date=datetime.date(2026, 5, 20),
        amount=Decimal(amount),
        description=description,
    )


def test_generated_id_is_stable_between_runs() -> None:
    first_run_id = generate_id(domain.TransactionIdGenerator())
    second_run_id = generate_id(domain.TransactionIdGenerator())

    assert first_run_id == second_run_id
    assert first_run_id.endswith('-1')


def test_generated_id_does_not_depend_on_amount_notation() -> None:
    assert generate_id(domain.TransactionIdGenerator(), amount='1000') == generate_id(
        domain.TransactionIdGenerator(), amount='1000.00'
    )


def test_generated_id_differs_for_different_operations() -> None:
    generator = domain.TransactionIdGenerator()

    assert generate_id(generator, amount='1000.00') != generate_id(generator, amount='-1000.00')
    assert generate_id(generator, description='Пополнение') != generate_id(generator, description='Проценты')


def test_identical_operations_get_sequential_numbers() -> None:
    generator = domain.TransactionIdGenerator()

    first_id = generate_id(generator)
    second_id = generate_id(generator)

    assert first_id.endswith('-1')
    assert second_id.endswith('-2')
    assert first_id.removesuffix('-1') == second_id.removesuffix('-2')
