import enum
from dataclasses import dataclass, field

from .consent import Consent
from .period import Period
from .transaction import ExtractionSource


class ProductExtractionStatus(enum.StrEnum):
    COMPLETE = 'complete'
    PARTIAL = 'partial'
    FAILED = 'failed'


@dataclass
class ProductReport:
    product_id: str
    masked_number: str
    status: ProductExtractionStatus
    extraction_source: ExtractionSource
    transactions_count: int


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
