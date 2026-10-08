import datetime
import enum
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from .period import Period

GENERATED_ID_LENGTH = 16


class TransactionType(enum.StrEnum):
    DEBIT = 'debit'
    CREDIT = 'credit'


class TransactionStatus(enum.StrEnum):
    POSTED = 'posted'
    PENDING = 'pending'
    DECLINED = 'declined'
    UNKNOWN = 'unknown'


class TransactionCategory(enum.StrEnum):
    TOP_UP = 'top_up'
    INTEREST = 'interest'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'
    SALARY = 'salary'
    GROCERIES = 'groceries'
    RESTAURANTS = 'restaurants'
    TRANSPORT = 'transport'
    SHOPPING = 'shopping'
    REFUND = 'refund'
    UTILITIES = 'utilities'
    FEE = 'fee'
    OTHER = 'other'


class TransactionIdSource(enum.StrEnum):
    BANK = 'bank'
    GENERATED = 'generated'


class ExtractionSource(enum.StrEnum):
    EXPORT = 'export'
    SERVER_RESPONSE = 'server_response'
    PAGE = 'page'


@dataclass
class Transaction:
    transaction_id: str
    id_source: TransactionIdSource
    product_id: str
    operation_date: datetime.date
    posting_date: datetime.date | None  # нет у операций в обработке и отклонённых
    amount: Decimal  # минус — списание
    currency: str
    type: TransactionType
    description: str
    counterparty: str | None
    category: TransactionCategory
    status: TransactionStatus
    is_duplicate: bool = False


@dataclass
class TransactionHistory:
    """Операции одного продукта, как их отдал банк, и способ, которым они получены."""

    transactions: list[Transaction]
    source: ExtractionSource
    warnings: list[str] = field(default_factory=list)
    incomplete_reason: str | None = None  # история получена не вся, например кабинет не дал подгрузить остаток


@dataclass
class PeriodSplit:
    inside: list[Transaction]
    outside: list[Transaction]


def split_by_period(transactions: list[Transaction], period: Period) -> PeriodSplit:
    split = PeriodSplit(inside=[], outside=[])
    for transaction in transactions:
        if period.contains_transaction_dates(transaction.operation_date, transaction.posting_date):
            split.inside.append(transaction)
        else:
            split.outside.append(transaction)
    return split


def transaction_type_for_amount(amount: Decimal) -> TransactionType:
    return TransactionType.DEBIT if amount < 0 else TransactionType.CREDIT


@dataclass
class TransactionIdGenerator:
    """Устойчивые идентификаторы операций одного продукта, у которых нет банковского.

    Одинаковые по полям операции различаются порядковым номером: '<хеш>-1', '<хеш>-2'.
    Дата проведения не участвует: иначе идентификатор менялся бы, когда операцию «в обработке» проводят.
    """

    occurrences: Counter[str] = field(default_factory=Counter)

    def next_id(
        self,
        product_id: str,
        operation_date: datetime.date,
        amount: Decimal,
        description: str,
    ) -> str:
        key_parts = [
            product_id,
            operation_date.isoformat(),
            f'{amount:.2f}',
            description,
        ]
        fingerprint = hashlib.sha256('|'.join(key_parts).encode()).hexdigest()[:GENERATED_ID_LENGTH]
        self.occurrences[fingerprint] += 1
        return f'{fingerprint}-{self.occurrences[fingerprint]}'
