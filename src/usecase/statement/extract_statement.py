import datetime
import logging
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
    extracted_at = datetime.datetime.now(datetime.UTC)
    log.info('Products extracted', extra={'products_count': len(products)})

    statement = domain.Statement(bank=input.bank, extracted_at=extracted_at, period=period, products=products)
    report = domain.ExtractionReport(bank=input.bank, period=period, consent=consent, products_count=len(products))

    folder_name = domain.build_run_folder_name(input.bank, started_at)
    statement_content = dto.StatementOutput.from_domain(statement).model_dump()
    report_content = dto.ExtractionReportOutput.from_domain(report).model_dump()
    output_folder = await self.storage.save_json(folder_name, STATEMENT_FILE_NAME, statement_content)
    await self.storage.save_json(folder_name, REPORT_FILE_NAME, report_content)
    log.info('Statement saved', extra={'output_folder': output_folder})

    return dto.ExtractStatementOutput(output_folder=output_folder, products_count=len(products))


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
