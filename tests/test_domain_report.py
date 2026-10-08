import datetime

from src import domain

PERIOD = domain.Period(date_from=datetime.date(2026, 5, 1), date_to=datetime.date(2026, 6, 30))
CONSENT = domain.Consent(
    bank_name='Демо-банк',
    period=PERIOD,
    scope=['Операции за выбранный период'],
    granted_at=datetime.datetime(2026, 7, 1, 9, 0, tzinfo=datetime.UTC),
)


def make_product_report(
    status: domain.ProductExtractionStatus = domain.ProductExtractionStatus.COMPLETE,
) -> domain.ProductReport:
    return domain.ProductReport(
        product_id='acc-rub',
        masked_number='**** 4567',
        status=status,
        extraction_source=domain.ExtractionSource.EXPORT,
        transactions_count=9,
    )


def make_report(
    products: list[domain.ProductReport], warnings: list[str] | None = None, errors: list[str] | None = None
) -> domain.ExtractionReport:
    return domain.ExtractionReport(
        bank='demo_bank',
        period=PERIOD,
        consent=CONSENT,
        products_count=len(products),
        transactions_count=9,
        duration_seconds=12.5,
        products=products,
        warnings=warnings or [],
        errors=errors or [],
    )


def test_report_without_warnings_errors_and_gaps_is_complete() -> None:
    report = make_report([make_product_report()])

    assert report.is_complete() is True


def test_report_with_warning_is_not_complete() -> None:
    report = make_report([make_product_report()], warnings=['Продукт card-debit: операция c-001 совпадает'])

    assert report.is_complete() is False


def test_report_with_error_is_not_complete() -> None:
    report = make_report([make_product_report()], errors=['Продукт loan: история не загружена'])

    assert report.is_complete() is False


def test_report_with_partially_extracted_product_is_not_complete() -> None:
    report = make_report([make_product_report(), make_product_report(domain.ProductExtractionStatus.PARTIAL)])

    assert report.is_complete() is False
