from collections import Counter
from dataclasses import dataclass

from .product import Product
from .transaction import Transaction


@dataclass
class ConsistencyProblems:
    """Нарушения согласованности готовой выписки; выписка с ними всё равно сохраняется."""

    repeated_transaction_ids: list[str]
    currency_mismatches: list[Transaction]  # валюта операции не совпадает с валютой её продукта
    missing_linked_accounts: list[Product]  # карты, привязанный счёт которых не найден среди продуктов

    def is_empty(self) -> bool:
        return not (self.repeated_transaction_ids or self.currency_mismatches or self.missing_linked_accounts)


def check_statement_consistency(products: list[Product], transactions: list[Transaction]) -> ConsistencyProblems:
    id_counts = Counter(transaction.transaction_id for transaction in transactions)
    repeated_ids = [transaction_id for transaction_id, count in id_counts.items() if count > 1]

    currency_by_product_id = {product.product_id: product.currency for product in products}
    currency_mismatches = [
        transaction
        for transaction in transactions
        if transaction.product_id in currency_by_product_id
        and transaction.currency != currency_by_product_id[transaction.product_id]
    ]

    missing_linked_accounts = [
        product
        for product in products
        if product.linked_account_id is not None and product.linked_account_id not in currency_by_product_id
    ]
    return ConsistencyProblems(
        repeated_transaction_ids=repeated_ids,
        currency_mismatches=currency_mismatches,
        missing_linked_accounts=missing_linked_accounts,
    )
