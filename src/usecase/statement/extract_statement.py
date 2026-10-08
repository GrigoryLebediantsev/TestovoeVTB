import datetime
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src import domain, dto

if TYPE_CHECKING:
    from .. import Usecase

log = logging.getLogger(__name__)

STATEMENT_FILE_NAME = 'statement.json'
PRODUCTS_FILE_NAME = 'products.csv'
TRANSACTIONS_FILE_NAME = 'transactions.csv'
REPORT_FILE_NAME = 'extraction_report.json'
DURATION_PRECISION_DIGITS = 1


async def extract_statement(self: Usecase, input: dto.ExtractStatementInput) -> dto.ExtractStatementOutput:
    """Выписка от согласия клиента до записи файлов; итог или причину неудачи клиент видит в браузере."""
    try:
        return await _extract_and_save(self, input)
    except domain.DomainError as error:
        await self.client_window.show_failure(str(error))
        raise


async def _extract_and_save(self: Usecase, input: dto.ExtractStatementInput) -> dto.ExtractStatementOutput:
    started_at = datetime.datetime.now(datetime.UTC)
    period = domain.Period(date_from=input.period_from, date_to=input.period_to)

    consent = await _ask_consent(self, period)
    log.info('Consent granted', extra={'bank': input.bank})

    await self.bank.wait_for_login()
    log.info('Client logged in')

    product_ids = await self.bank.get_product_ids()
    log.info('Products found', extra={'products_count': len(product_ids)})

    products: list[domain.Product] = []
    transactions: list[domain.Transaction] = []
    product_reports: list[domain.ProductReport] = []
    warnings: list[str] = []
    errors: list[str] = []
    for product_id in product_ids:
        product_extraction = await _extract_product(self, product_id, period)
        if product_extraction.product is not None:
            products.append(product_extraction.product)
        transactions.extend(product_extraction.transactions)
        product_reports.append(product_extraction.report)
        warnings.extend(product_extraction.warnings)
        errors.extend(product_extraction.errors)
    warnings.extend(_mark_card_duplicates(products, transactions))
    extracted_at = datetime.datetime.now(datetime.UTC)
    duration_seconds = round((extracted_at - started_at).total_seconds(), DURATION_PRECISION_DIGITS)

    statement = domain.Statement(
        bank=input.bank, extracted_at=extracted_at, period=period, products=products, transactions=transactions
    )
    report = domain.ExtractionReport(
        bank=input.bank,
        period=period,
        consent=consent,
        products_count=len(products),
        transactions_count=len(transactions),
        duration_seconds=duration_seconds,
        products=product_reports,
        warnings=warnings,
        errors=errors,
    )

    folder_name = domain.build_run_folder_name(input.bank, started_at)
    await _save_statement(self, folder_name, statement, input.format)
    report_content = dto.ExtractionReportOutput.from_domain(report).model_dump()
    output_folder = await self.storage.save_json(folder_name, REPORT_FILE_NAME, report_content)
    log.info('Statement saved', extra={'output_folder': output_folder, 'format': input.format})
    await self.client_window.show_summary(self.bank.display_name, report)

    return dto.ExtractStatementOutput(
        output_folder=output_folder,
        products_count=len(products),
        transactions_count=len(transactions),
        warnings_count=len(report.warnings),
        errors_count=len(report.errors),
        is_complete=report.is_complete(),
    )


async def _save_statement(
    self: Usecase, folder_name: str, statement: domain.Statement, statement_format: domain.StatementFormat
) -> None:
    if statement_format.includes_json():
        statement_content = dto.StatementOutput.from_domain(statement).model_dump()
        await self.storage.save_json(folder_name, STATEMENT_FILE_NAME, statement_content)
    if statement_format.includes_csv():
        product_rows = [dto.ProductCsvRowOutput.from_domain(product).model_dump() for product in statement.products]
        transaction_rows = [
            dto.TransactionOutput.from_domain(transaction).model_dump() for transaction in statement.transactions
        ]
        await self.storage.save_csv(
            folder_name, PRODUCTS_FILE_NAME, list(dto.ProductCsvRowOutput.model_fields), product_rows
        )
        await self.storage.save_csv(
            folder_name, TRANSACTIONS_FILE_NAME, list(dto.TransactionOutput.model_fields), transaction_rows
        )


@dataclass
class _ProductExtraction:
    product: domain.Product | None  # нет, если карточку продукта получить не удалось
    transactions: list[domain.Transaction]
    report: domain.ProductReport
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


async def _extract_product(self: Usecase, product_id: str, period: domain.Period) -> _ProductExtraction:
    """Карточка продукта, его операции за период, строка отчёта о нём, предупреждения и ошибки.

    Сбой одного продукта не останавливает запуск: продукт помечается как failed с причиной.
    """
    try:
        product = await self.bank.get_product(product_id)
    except domain.ExternalServiceError as error:
        log.error('Product not extracted: %s', type(error).__name__, extra={'product_id': product_id})
        return _ProductExtraction(
            product=None,
            transactions=[],
            report=domain.ProductReport.failed(product_id, masked_number=None, reason=str(error)),
            errors=[f'Продукт {product_id}: {error}'],
        )

    try:
        history = await self.bank.get_transactions(product_id, period)
    except domain.ExternalServiceError as error:
        log.error('Transactions not extracted: %s', type(error).__name__, extra={'product_id': product_id})
        return _ProductExtraction(
            product=product,
            transactions=[],
            report=domain.ProductReport.failed(product_id, product.masked_number, reason=str(error)),
            errors=[f'Продукт {product_id}: {error}'],
        )

    period_split = domain.split_by_period(history.transactions, period)
    warnings = list(history.warnings)
    if history.incomplete_reason:
        warnings.append(f'Продукт {product.product_id}: {history.incomplete_reason}')
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
    product_report = domain.ProductReport.from_history(product, history, transactions_count=len(period_split.inside))
    return _ProductExtraction(
        product=product, transactions=period_split.inside, report=product_report, warnings=warnings
    )


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


def _mark_card_duplicates(products: list[domain.Product], transactions: list[domain.Transaction]) -> list[str]:
    """Помечает копии на карте операций, видимых и на привязанном счёте; возвращает предупреждения."""
    pairs = domain.find_card_duplicates(products, transactions)
    warnings = []
    for pair in pairs:
        pair.card_transaction.is_duplicate = True
        warnings.append(
            f'Продукт {pair.card_transaction.product_id}: операция {pair.card_transaction.transaction_id} '
            f'совпадает с операцией {pair.account_transaction.transaction_id} '
            f'продукта {pair.account_transaction.product_id}'
        )
    log.info('Card duplicates marked', extra={'duplicates_count': len(pairs)})
    return warnings
