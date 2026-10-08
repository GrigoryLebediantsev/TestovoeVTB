from src.usecase import Usecase

_usecase: Usecase | None = None


def set_usecase(usecase: Usecase) -> None:
    global _usecase
    _usecase = usecase


def get_usecase() -> Usecase:
    if _usecase is None:
        raise RuntimeError('Usecase is not initialized')
    return _usecase
