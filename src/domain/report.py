from dataclasses import dataclass

from .consent import Consent
from .period import Period


@dataclass
class ExtractionReport:
    bank: str
    period: Period
    consent: Consent
    products_count: int
