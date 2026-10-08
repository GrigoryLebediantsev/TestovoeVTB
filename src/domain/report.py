import enum
from dataclasses import dataclass, field

from .consent import Consent
from .period import Period
from .product import Product
from .transaction import ExtractionSource, TransactionHistory


class ProductExtractionStatus(enum.StrEnum):
    COMPLETE = 'complete'
    PARTIAL = 'partial'
    FAILED = 'failed'


@dataclass
class ProductReport:
    product_id: str
    masked_number: str | None  # нет у продукта, карточку которого получить не удалось
    status: ProductExtractionStatus
    extraction_source: ExtractionSource | None  # нет у продукта, историю которого получить не удалось
    transactions_count: int
    reason: str | None = None  # почему продукт извлечён не полностью или не извлечён

    @classmethod
    def from_history(cls, product: Product, history: TransactionHistory, transactions_count: int) -> ProductReport:
        """Продукт, история которого получена: полностью или с пропусками."""
        is_partial = history.incomplete_reason is not None
        return cls(
            product_id=product.product_id,
            masked_number=product.masked_number,
            status=ProductExtractionStatus.PARTIAL if is_partial else ProductExtractionStatus.COMPLETE,
            extraction_source=history.source,
            transactions_count=transactions_count,
            reason=history.incomplete_reason,
        )

    @classmethod
    def failed(cls, product_id: str, masked_number: str | None, reason: str) -> ProductReport:
        """Продукт, карточку или историю которого получить не удалось."""
        return cls(
            product_id=product_id,
            masked_number=masked_number,
            status=ProductExtractionStatus.FAILED,
            extraction_source=None,
            transactions_count=0,
            reason=reason,
        )


@dataclass
class ExtractionReport:
    bank: str
    period: Period
    consent: Consent
    products_count: int
    transactions_count: int
    duration_seconds: float
    products: list[ProductReport] = field(default_factory=list)
    # Только маскированные значения
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Всё извлечено полностью: ни предупреждений, ни ошибок, ни продуктов с пропусками."""
        if self.warnings or self.errors:
            return False
        return all(product.status == ProductExtractionStatus.COMPLETE for product in self.products)
