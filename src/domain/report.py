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
    products: list[ProductReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # только маскированные значения
