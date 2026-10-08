"""Чтение выписки запуска и эталонной выписки из JSON-файлов для оценки качества."""

import datetime
import json
import logging
from decimal import Decimal
from pathlib import Path

import pydantic

from src import domain
from src.usecase import StatementFiles

log = logging.getLogger(__name__)

STATEMENT_FILE_NAME = 'statement.json'
REPORT_FILE_NAME = 'extraction_report.json'


class PeriodContent(pydantic.BaseModel):
    date_from: datetime.date = pydantic.Field(alias='from')
    date_to: datetime.date = pydantic.Field(alias='to')

    def to_domain(self) -> domain.Period:
        return domain.Period(date_from=self.date_from, date_to=self.date_to)


class TransactionContent(pydantic.BaseModel):
    """Операция в единой схеме: так её пишет прототип и так она записана в эталоне."""

    product_id: str
    operation_date: datetime.date
    amount: Decimal
    currency: str
    posting_date: datetime.date | None
    type: domain.TransactionType
    description: str
    counterparty: str | None
    category: domain.TransactionCategory
    status: domain.TransactionStatus

    def to_domain(self) -> domain.ComparableTransaction:
        return domain.ComparableTransaction(
            product_id=self.product_id,
            operation_date=self.operation_date,
            amount=self.amount,
            currency=self.currency,
            posting_date=self.posting_date,
            type=self.type,
            description=self.description,
            counterparty=self.counterparty,
            category=self.category,
            status=self.status,
        )


class StatementContent(pydantic.BaseModel):
    """statement.json и эталонная выписка: период и операции, остальные поля не нужны."""

    period: PeriodContent
    transactions: list[TransactionContent]


class ReportContent(pydantic.BaseModel):
    warnings: list[str]


class JsonStatementFiles(StatementFiles):
    @staticmethod
    async def read_extracted_statement(path: str) -> domain.ExtractedStatement:
        statement_path = Path(path)
        if statement_path.is_dir():
            statement_path = statement_path / STATEMENT_FILE_NAME
        statement = _read_json_file(statement_path, StatementContent)
        report = _read_json_file(statement_path.parent / REPORT_FILE_NAME, ReportContent)
        return domain.ExtractedStatement(
            period=statement.period.to_domain(),
            transactions=[transaction.to_domain() for transaction in statement.transactions],
            warnings_count=len(report.warnings),
        )

    @staticmethod
    async def read_reference_statement(path: str) -> domain.ReferenceStatement:
        reference = _read_json_file(Path(path), StatementContent)
        return domain.ReferenceStatement(
            period=reference.period.to_domain(),
            transactions=[transaction.to_domain() for transaction in reference.transactions],
        )


def _read_json_file[T: pydantic.BaseModel](path: Path, content_class: type[T]) -> T:
    if not path.is_file():
        raise domain.EvaluationFileNotFound(str(path))
    try:
        # Суммы читаем как Decimal: через float 6890.41 потеряло бы точность
        data = json.loads(path.read_text(encoding='utf-8'), parse_float=Decimal)
        return content_class.model_validate(data)
    except (ValueError, UnicodeDecodeError) as error:
        log.error('Evaluation file not recognized: %s', type(error).__name__, extra={'path': str(path)})
        raise domain.EvaluationFileInvalid(str(path)) from error
