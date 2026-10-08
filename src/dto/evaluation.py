import pydantic

from src import domain


class EvaluateStatementInput(pydantic.BaseModel):
    statement_path: str = pydantic.Field(description='Папка результата запуска или файл statement.json')
    reference_path: str


class EvaluateStatementOutput(pydantic.BaseModel):
    extracted_count: int
    reference_count: int
    matched_count: int
    precision: float
    recall: float
    normalized_fields_share: float
    warnings_count: int

    @classmethod
    def from_domain(cls, evaluation: domain.TransactionsEvaluation, warnings_count: int) -> EvaluateStatementOutput:
        return cls(
            extracted_count=evaluation.extracted_count,
            reference_count=evaluation.reference_count,
            matched_count=evaluation.matched_count,
            precision=evaluation.precision,
            recall=evaluation.recall,
            normalized_fields_share=evaluation.normalized_fields_share,
            warnings_count=warnings_count,
        )
