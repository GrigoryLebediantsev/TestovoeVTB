import logging
from typing import TYPE_CHECKING

from src import domain, dto

if TYPE_CHECKING:
    from .. import EvaluationUsecase

log = logging.getLogger(__name__)


async def evaluate_statement(self: EvaluationUsecase, input: dto.EvaluateStatementInput) -> dto.EvaluateStatementOutput:
    """Сравнивает выписку запуска с эталонной: эталон берётся только за период выписки."""
    extracted = await self.statement_files.read_extracted_statement(input.statement_path)
    if extracted is None:
        raise domain.EvaluationFileNotFound(input.statement_path)
    reference = await self.statement_files.read_reference_statement(input.reference_path)
    if reference is None:
        raise domain.EvaluationFileNotFound(input.reference_path)
    if not reference.covers(extracted.period):
        raise domain.ReferencePeriodNotCovered()

    evaluation = domain.evaluate_transactions(extracted.transactions, reference.transactions_in(extracted.period))
    log.info(
        'Statement evaluated',
        extra={
            'extracted_count': evaluation.extracted_count,
            'reference_count': evaluation.reference_count,
            'matched_count': evaluation.matched_count,
        },
    )
    return dto.EvaluateStatementOutput.from_domain(evaluation, warnings_count=extracted.warnings_count)
