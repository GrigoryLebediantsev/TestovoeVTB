from src.usecase import EvaluationUsecase, Usecase

_usecase: Usecase | None = None
_evaluation_usecase: EvaluationUsecase | None = None


def set_usecase(usecase: Usecase) -> None:
    global _usecase
    _usecase = usecase


def get_usecase() -> Usecase:
    if _usecase is None:
        raise RuntimeError('Usecase is not initialized')
    return _usecase


def set_evaluation_usecase(usecase: EvaluationUsecase) -> None:
    global _evaluation_usecase
    _evaluation_usecase = usecase


def get_evaluation_usecase() -> EvaluationUsecase:
    if _evaluation_usecase is None:
        raise RuntimeError('Evaluation usecase is not initialized')
    return _evaluation_usecase
