import dataclasses
import datetime
from decimal import Decimal

import pytest

from src import domain

REFERENCE_PERIOD = domain.Period(date_from=datetime.date(2026, 3, 1), date_to=datetime.date(2026, 6, 30))
STATEMENT_PERIOD = domain.Period(date_from=datetime.date(2026, 5, 1), date_to=datetime.date(2026, 6, 30))


def make_transaction(
    operation_date: datetime.date = datetime.date(2026, 5, 3),
    amount: str = '-1450.00',
    description: str = 'Пятёрочка',
    status: domain.TransactionStatus = domain.TransactionStatus.POSTED,
) -> domain.ComparableTransaction:
    return domain.ComparableTransaction(
        product_id='card-debit',
        operation_date=operation_date,
        amount=Decimal(amount),
        currency='RUB',
        posting_date=operation_date,
        type=domain.TransactionType.DEBIT,
        description=description,
        counterparty='Пятёрочка',
        category=domain.TransactionCategory.GROCERIES,
        status=status,
    )


PURCHASE = make_transaction()
TAXI = make_transaction(operation_date=datetime.date(2026, 5, 10), amount='-350.00', description='Такси')
COFFEE = make_transaction(operation_date=datetime.date(2026, 6, 2), amount='-200.00', description='Кофе')


def test_identical_transactions_give_full_scores() -> None:
    evaluation = domain.evaluate_transactions([PURCHASE, TAXI], [PURCHASE, TAXI])

    assert evaluation.matched_count == 2
    assert evaluation.precision == 1.0
    assert evaluation.recall == 1.0
    assert evaluation.normalized_fields_share == 1.0


def test_extra_transaction_lowers_precision() -> None:
    evaluation = domain.evaluate_transactions([PURCHASE, TAXI, COFFEE], [PURCHASE, TAXI])

    assert evaluation.precision == pytest.approx(2 / 3)
    assert evaluation.recall == 1.0


def test_missing_transaction_lowers_recall() -> None:
    evaluation = domain.evaluate_transactions([PURCHASE], [PURCHASE, TAXI])

    assert evaluation.precision == 1.0
    assert evaluation.recall == 0.5


def test_wrong_field_lowers_normalized_share_but_not_matching() -> None:
    unknown_status = dataclasses.replace(PURCHASE, status=domain.TransactionStatus.UNKNOWN)

    evaluation = domain.evaluate_transactions([unknown_status, TAXI], [PURCHASE, TAXI])

    assert evaluation.precision == 1.0
    assert evaluation.recall == 1.0
    compared_fields_count = 2 * len(domain.COMPARED_TRANSACTION_FIELDS)
    assert evaluation.normalized_fields_share == pytest.approx((compared_fields_count - 1) / compared_fields_count)


def test_same_key_transactions_are_counted_by_occurrence() -> None:
    # Две одинаковые операции в эталоне, одна в выписке: найдена одна из двух
    evaluation = domain.evaluate_transactions([PURCHASE], [PURCHASE, PURCHASE])

    assert evaluation.matched_count == 1
    assert evaluation.recall == 0.5


def test_same_key_transactions_are_paired_by_best_fields() -> None:
    other_description = dataclasses.replace(PURCHASE, description='Магнит')

    evaluation = domain.evaluate_transactions([other_description, PURCHASE], [PURCHASE, other_description])

    assert evaluation.normalized_fields_share == 1.0


def test_empty_statement_has_full_precision_and_zero_recall() -> None:
    evaluation = domain.evaluate_transactions([], [PURCHASE])

    assert evaluation.precision == 1.0
    assert evaluation.recall == 0.0


def test_reference_is_cut_by_statement_period_by_posting_date() -> None:
    april_purchase = make_transaction(operation_date=datetime.date(2026, 4, 29))
    # Совершена до периода, но проведена в нём — в периоде, как и в выписке
    posted_in_may = dataclasses.replace(
        make_transaction(operation_date=datetime.date(2026, 4, 30)), posting_date=datetime.date(2026, 5, 1)
    )
    reference = domain.ReferenceStatement(
        period=REFERENCE_PERIOD, transactions=[april_purchase, posted_in_may, PURCHASE]
    )

    assert reference.covers(STATEMENT_PERIOD) is True
    assert reference.transactions_in(STATEMENT_PERIOD) == [posted_in_may, PURCHASE]


def test_reference_uses_operation_date_without_posting_date() -> None:
    pending_on_last_day = dataclasses.replace(
        make_transaction(operation_date=datetime.date(2026, 6, 30)), posting_date=None
    )
    pending_in_april = dataclasses.replace(
        make_transaction(operation_date=datetime.date(2026, 4, 30)), posting_date=None
    )
    reference = domain.ReferenceStatement(period=REFERENCE_PERIOD, transactions=[pending_in_april, pending_on_last_day])

    assert reference.transactions_in(STATEMENT_PERIOD) == [pending_on_last_day]


def test_reference_does_not_cover_longer_period() -> None:
    reference = domain.ReferenceStatement(period=REFERENCE_PERIOD, transactions=[])
    july_period = domain.Period(date_from=datetime.date(2026, 6, 1), date_to=datetime.date(2026, 7, 31))

    assert reference.covers(july_period) is False
