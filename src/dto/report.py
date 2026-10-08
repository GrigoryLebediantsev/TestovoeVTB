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


class ExtractionReportOutput(pydantic.BaseModel):
    bank: str
    period: PeriodOutput
    consent: ConsentOutput
    products_count: int

    @classmethod
    def from_domain(cls, report: domain.ExtractionReport) -> ExtractionReportOutput:
        return cls(
            bank=report.bank,
            period=PeriodOutput.from_domain(report.period),
            consent=ConsentOutput.from_domain(report.consent),
            products_count=report.products_count,
        )
