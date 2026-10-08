"""Оценка качества извлечения: сравнение выписки с эталонной."""

import datetime
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .period import Period
from .transaction import TransactionCategory, TransactionStatus, TransactionType

# Продукт, дата операции, сумма и валюта: по ним операция выписки сопоставляется с эталонной
TransactionMatchKey = tuple[str, datetime.date, Decimal, str]
# Нормализованные поля, которые сверяются у сопоставленных операций
COMPARED_TRANSACTION_FIELDS = ('posting_date', 'type', 'description', 'counterparty', 'category', 'status')


@dataclass(frozen=True)
class ComparableTransaction:
    """Операция для сравнения с эталоном: ключ сопоставления и нормализованные поля."""

    product_id: str
    operation_date: datetime.date
    amount: Decimal
    currency: str
    posting_date: datetime.date | None
    type: TransactionType
    description: str
    counterparty: str | None
    category: TransactionCategory
    status: TransactionStatus

    def match_key(self) -> TransactionMatchKey:
        """Операция «найдена», если совпали продукт, дата операции, сумма и валюта."""
        return (self.product_id, self.operation_date, self.amount, self.currency)

    def count_equal_fields(self, other: ComparableTransaction) -> int:
        return sum(getattr(self, name) == getattr(other, name) for name in COMPARED_TRANSACTION_FIELDS)


@dataclass
class ExtractedStatement:
    """Выписка запуска прототипа в том виде, который нужен для оценки."""

    period: Period
    transactions: list[ComparableTransaction]
    warnings_count: int


@dataclass
class ReferenceStatement:
    period: Period
    transactions: list[ComparableTransaction]

    def covers(self, period: Period) -> bool:
        return self.period.date_from <= period.date_from and period.date_to <= self.period.date_to

    def transactions_in(self, period: Period) -> list[ComparableTransaction]:
        """Эталонные операции периода: по дате операции, как прототип отбрасывает операции вне периода."""
        return [
            transaction
            for transaction in self.transactions
            if period.date_from <= transaction.operation_date <= period.date_to
        ]


@dataclass(frozen=True)
class TransactionsEvaluation:
    extracted_count: int
    reference_count: int
    matched_count: int
    compared_fields_count: int
    equal_fields_count: int

    @property
    def precision(self) -> float:
        """Доля операций выписки, которые есть в эталоне."""
        return _share(self.matched_count, self.extracted_count)

    @property
    def recall(self) -> float:
        """Доля операций эталона, которые нашлись в выписке."""
        return _share(self.matched_count, self.reference_count)

    @property
    def normalized_fields_share(self) -> float:
        """Доля полей сопоставленных операций, совпавших с эталоном."""
        return _share(self.equal_fields_count, self.compared_fields_count)


def evaluate_transactions(
    extracted: list[ComparableTransaction], reference: list[ComparableTransaction]
) -> TransactionsEvaluation:
    """Сопоставляет операции по ключу; одинаковые по ключу считаются по количеству, пара — с наибольшим совпадением."""
    unmatched_by_key: dict[TransactionMatchKey, list[ComparableTransaction]] = defaultdict(list)
    for reference_transaction in reference:
        unmatched_by_key[reference_transaction.match_key()].append(reference_transaction)

    matched_count = 0
    equal_fields_count = 0
    for transaction in extracted:
        candidates = unmatched_by_key[transaction.match_key()]
        if not candidates:
            continue
        best_candidate = max(candidates, key=transaction.count_equal_fields)
        candidates.remove(best_candidate)
        matched_count += 1
        equal_fields_count += transaction.count_equal_fields(best_candidate)

    return TransactionsEvaluation(
        extracted_count=len(extracted),
        reference_count=len(reference),
        matched_count=matched_count,
        compared_fields_count=matched_count * len(COMPARED_TRANSACTION_FIELDS),
        equal_fields_count=equal_fields_count,
    )


def _share(part: int, whole: int) -> float:
    """Пустое множество считается полностью верным: нет ни одной ошибки."""
    return part / whole if whole else 1.0
