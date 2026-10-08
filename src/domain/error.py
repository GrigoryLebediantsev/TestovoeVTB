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
