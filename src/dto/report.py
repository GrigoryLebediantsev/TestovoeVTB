import datetime

import pydantic

from src import domain

from .statement import PeriodOutput


class ConsentOutput(pydantic.BaseModel):
    granted_at: datetime.datetime
    scope: list[str] = pydantic.Field(default_factory=list)

    @classmethod
    def from_domain(cls, consent: domain.Consent) -> ConsentOutput:
        return cls(granted_at=consent.granted_at, scope=consent.scope)


class ProductReportOutput(pydantic.BaseModel):
    product_id: str
    status: domain.ProductExtractionStatus
    extraction_source: domain.ExtractionSource
    transactions_count: int

    @classmethod
    def from_domain(cls, product_report: domain.ProductReport) -> ProductReportOutput:
        return cls(
            product_id=product_report.product_id,
            status=product_report.status,
            extraction_source=product_report.extraction_source,
            transactions_count=product_report.transactions_count,
        )


class ExtractionReportOutput(pydantic.BaseModel):
    bank: str
    period: PeriodOutput
    consent: ConsentOutput
    products_count: int
    transactions_count: int
    products: list[ProductReportOutput] = pydantic.Field(default_factory=list)
    warnings: list[str] = pydantic.Field(default_factory=list)

    @classmethod
    def from_domain(cls, report: domain.ExtractionReport) -> ExtractionReportOutput:
        return cls(
            bank=report.bank,
            period=PeriodOutput.from_domain(report.period),
            consent=ConsentOutput.from_domain(report.consent),
            products_count=report.products_count,
            transactions_count=report.transactions_count,
            products=[ProductReportOutput.from_domain(product_report) for product_report in report.products],
            warnings=report.warnings,
        )
