import typing
from dataclasses import dataclass

from src import domain

from .statement.extract_statement import extract_statement


class Bank(typing.Protocol):
    display_name: str

    async def wait_for_login(self) -> None:
        """Открывает страницу входа и ждёт, пока клиент сам войдёт; при таймауте — domain.LoginTimeout."""
        ...

    async def get_products(self) -> list[domain.Product]: ...

    async def get_transactions(self, product_id: str, period: domain.Period) -> domain.TransactionHistory:
        """Операции продукта в единой схеме; фильтр периода выставляется в кабинете, если он там есть."""
        ...


class ClientWindow(typing.Protocol):
    async def ask_consent(self, bank_name: str, period: domain.Period, scope: list[str]) -> bool:
        """Показывает клиенту страницу согласия; True — «Разрешаю», False — «Отказываюсь»."""
        ...


class ResultStorage(typing.Protocol):
    async def save_json(self, folder_name: str, file_name: str, content: dict[str, object]) -> str:
        """Сохраняет JSON-файл в папку запуска и возвращает путь к этой папке."""
        ...

    async def save_csv(
        self, folder_name: str, file_name: str, columns: list[str], rows: list[dict[str, object]]
    ) -> str:
        """Сохраняет CSV-таблицу в папку запуска и возвращает путь к этой папке."""
        ...


@dataclass
class Usecase:
    bank: Bank
    client_window: ClientWindow
    storage: ResultStorage

    # Statement
    extract_statement = extract_statement
