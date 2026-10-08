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


PRODUCT = domain.Product(
    product_id='acc-usd',
    type=domain.ProductType.ACCOUNT,
    name='Счёт в долларах',
    masked_number='**** 4321',
    currency='USD',
)


def test_product_report_for_full_history_is_complete() -> None:
    history = domain.TransactionHistory(transactions=[], source=domain.ExtractionSource.SERVER_RESPONSE)

    product_report = domain.ProductReport.from_history(PRODUCT, history, transactions_count=12)

    assert product_report == domain.ProductReport(
        product_id='acc-usd',
        masked_number='**** 4321',
        status=domain.ProductExtractionStatus.COMPLETE,
        extraction_source=domain.ExtractionSource.SERVER_RESPONSE,
        transactions_count=12,
    )


def test_product_report_for_incomplete_history_is_partial_with_reason() -> None:
    history = domain.TransactionHistory(
        transactions=[],
        source=domain.ExtractionSource.SERVER_RESPONSE,
        incomplete_reason='история загружена не полностью',
    )

    product_report = domain.ProductReport.from_history(PRODUCT, history, transactions_count=5)

    assert product_report.status == domain.ProductExtractionStatus.PARTIAL
    assert product_report.reason == 'история загружена не полностью'
    assert product_report.transactions_count == 5


def test_failed_product_report_has_reason_and_no_source() -> None:
    product_report = domain.ProductReport.failed('acc-usd', '**** 4321', reason='история операций не загружена')

    assert product_report == domain.ProductReport(
        product_id='acc-usd',
        masked_number='**** 4321',
        status=domain.ProductExtractionStatus.FAILED,
        extraction_source=None,
        transactions_count=0,
        reason='история операций не загружена',
    )


def test_failed_product_report_without_details_has_no_masked_number() -> None:
    product_report = domain.ProductReport.failed('loan', None, reason='карточка продукта не загружена')

    assert product_report.masked_number is None
    assert product_report.status == domain.ProductExtractionStatus.FAILED
