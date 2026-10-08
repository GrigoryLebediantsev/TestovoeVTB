import datetime
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src import domain, dto

if TYPE_CHECKING:
    from .. import Usecase

log = logging.getLogger(__name__)

STATEMENT_FILE_NAME = 'statement.json'
REPORT_FILE_NAME = 'extraction_report.json'


async def extract_statement(self: Usecase, input: dto.ExtractStatementInput) -> dto.ExtractStatementOutput:
    started_at = datetime.datetime.now(datetime.UTC)
    period = domain.Period(date_from=input.period_from, date_to=input.period_to)

    consent = await _ask_consent(self, period)
    log.info('Consent granted', extra={'bank': input.bank})

    await self.bank.wait_for_login()
    log.info('Client logged in')

    products = await self.bank.get_products()
    log.info('Products extracted', extra={'products_count': len(products)})

    transactions: list[domain.Transaction] = []
    product_reports: list[domain.ProductReport] = []
    warnings: list[str] = []
    for product in products:
        product_extraction = await _extract_transactions(self, product, period)
        transactions.extend(product_extraction.transactions)
        product_reports.append(product_extraction.report)
        warnings.extend(product_extraction.warnings)
    extracted_at = datetime.datetime.now(datetime.UTC)

    statement = domain.Statement(
        bank=input.bank, extracted_at=extracted_at, period=period, products=products, transactions=transactions
    )
    report = domain.ExtractionReport(
        bank=input.bank,
        period=period,
        consent=consent,
        products_count=len(products),
        transactions_count=len(transactions),
        products=product_reports,
        warnings=warnings,
    )

    folder_name = domain.build_run_folder_name(input.bank, started_at)
    statement_content = dto.StatementOutput.from_domain(statement).model_dump()
    report_content = dto.ExtractionReportOutput.from_domain(report).model_dump()
    output_folder = await self.storage.save_json(folder_name, STATEMENT_FILE_NAME, statement_content)
    await self.storage.save_json(folder_name, REPORT_FILE_NAME, report_content)
    log.info('Statement saved', extra={'output_folder': output_folder})

    return dto.ExtractStatementOutput(
        output_folder=output_folder, products_count=len(products), transactions_count=len(transactions)
    )


@dataclass
class _ProductExtraction:
    transactions: list[domain.Transaction]
    report: domain.ProductReport
    warnings: list[str]


async def _extract_transactions(self: Usecase, product: domain.Product, period: domain.Period) -> _ProductExtraction:
    """Операции продукта за период, строка отчёта о нём и предупреждения."""
    history = await self.bank.get_transactions(product.product_id, period)
    period_split = domain.split_by_period(history.transactions, period)
    warnings = list(history.warnings)
    if period_split.outside:
        warnings.append(f'Продукт {product.product_id}: отброшено операций вне периода: {len(period_split.outside)}')

    log.info(
        'Transactions extracted',
        extra={
            'product_id': product.product_id,
            'extraction_source': history.source,
            'transactions_count': len(period_split.inside),
            'dropped_outside_period': len(period_split.outside),
        },
    )
    product_report = domain.ProductReport(
        product_id=product.product_id,
        status=domain.ProductExtractionStatus.COMPLETE,
        extraction_source=history.source,
        transactions_count=len(period_split.inside),
    )
    return _ProductExtraction(transactions=period_split.inside, report=product_report, warnings=warnings)


async def _ask_consent(self: Usecase, period: domain.Period) -> domain.Consent:
    scope = list(domain.CONSENT_SCOPE)
    is_granted = await self.client_window.ask_consent(self.bank.display_name, period, scope)
    if not is_granted:
        raise domain.ConsentRefused()
    return domain.Consent(
        bank_name=self.bank.display_name,
        period=period,
        scope=scope,
        granted_at=datetime.datetime.now(datetime.UTC),
    )
