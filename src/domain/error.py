class DomainError(Exception): ...


class AccessDeniedError(DomainError): ...


class ExternalServiceError(DomainError): ...


class ConsentRefused(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__('Клиент отказался от чтения данных')


class ConsentTimeout(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__('Клиент не ответил на запрос согласия')


class LoginTimeout(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__('Клиент не вошёл в личный кабинет за отведённое время')


class ProductsNotLoaded(ExternalServiceError):
    def __init__(self) -> None:
        super().__init__('Не удалось загрузить список продуктов')


# Ошибки одного продукта: продукт помечается в отчёте, остальные извлекаются дальше.
# Текст — причина в отчёте, без значений из кабинета.
class ProductDetailsNotLoaded(ExternalServiceError):
    def __init__(self) -> None:
        super().__init__('карточка продукта не загружена')


class TransactionsNotLoaded(ExternalServiceError):
    def __init__(self) -> None:
        super().__init__('история операций не загружена')


class TransactionsFormatNotRecognized(ExternalServiceError):
    def __init__(self) -> None:
        super().__init__('формат истории операций не распознан')


class TransactionsLayoutNotRecognized(ExternalServiceError):
    def __init__(self) -> None:
        super().__init__('разметка истории операций не распознана')
