import datetime
from dataclasses import dataclass
from decimal import Decimal

from .product import Product
from .transaction import Transaction, TransactionStatus


@dataclass
class DuplicatePair:
    """Операция карты и её копия в истории привязанного счёта; дубликатом помечается копия на карте."""

    card_transaction: Transaction
    account_transaction: Transaction


def find_card_duplicates(products: list[Product], transactions: list[Transaction]) -> list[DuplicatePair]:
    """Ищет операции карт, видимые и в истории привязанного счёта.

    Совпадение — дата операции, сумма и валюта: описание на карте и счёте обычно разное.
    Отклонённые не сравниваются: они не списывают деньги, копии на счёте у них нет.
    Каждая операция счёта сопоставляется не более чем с одной операцией карты.
    """
    comparable_transactions = [
        transaction for transaction in transactions if transaction.status != TransactionStatus.DECLINED
    ]
    pairs = []
    for card in products:
        if card.linked_account_id is None:
            continue
        unmatched_account_transactions = [
            transaction for transaction in comparable_transactions if transaction.product_id == card.linked_account_id
        ]
        for card_transaction in comparable_transactions:
            if card_transaction.product_id != card.product_id:
                continue
            account_transaction = _find_same_operation(card_transaction, unmatched_account_transactions)
            if account_transaction is None:
                continue
            unmatched_account_transactions.remove(account_transaction)
            pairs.append(DuplicatePair(card_transaction=card_transaction, account_transaction=account_transaction))
    return pairs


def _find_same_operation(card_transaction: Transaction, account_transactions: list[Transaction]) -> Transaction | None:
    card_key = _build_matching_key(card_transaction)
    for account_transaction in account_transactions:
        if _build_matching_key(account_transaction) == card_key:
            return account_transaction
    return None


def _build_matching_key(transaction: Transaction) -> tuple[datetime.date, Decimal, str]:
    return transaction.operation_date, transaction.amount, transaction.currency
