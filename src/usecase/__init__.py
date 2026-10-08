import typing
from dataclasses import dataclass

from src import domain

from .evaluation.evaluate_statement import evaluate_statement
from .statement.extract_statement import extract_statement


class Bank(typing.Protocol):
    display_name: str

    async def wait_for_login(self) -> None:
        """Открывает страницу входа и ждёт, пока клиент сам войдёт; при таймауте — domain.LoginTimeout."""
        ...

    async def get_product_ids(self) -> list[str]:
        """Продукты из списка в кабинете; список не загрузился — domain.ProductsNotLoaded."""
        ...

    async def get_product(self, product_id: str) -> domain.Product:
        """Карточка продукта; не загрузилась — domain.ProductDetailsNotLoaded."""
        ...

    async def get_transactions(self, product_id: str, period: domain.Period) -> domain.TransactionHistory:
        """Операции продукта в единой схеме; фильтр периода выставляется в кабинете, если он там есть.

        Сбой истории продукта — domain.ExternalServiceError с причиной для отчёта.
        """
        ...


class ClientWindow(typing.Protocol):
    async def ask_consent(self, bank_name: str, period: domain.Period, scope: list[str]) -> bool:
        """Показывает клиенту страницу согласия; True — «Разрешаю», False — «Отказываюсь»."""
        ...

    async def show_summary(self, bank_name: str, report: domain.ExtractionReport) -> None:
        """Итоговая страница без чувствительных данных; сбой показа не прерывает сценарий."""
        ...

    async def show_failure(self, reason: str) -> None:
        """Страница «Выписка не сформирована» с причиной; сбой показа не прерывает сценарий."""
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


class StatementFiles(typing.Protocol):
    async def read_extracted_statement(self, path: str) -> domain.ExtractedStatement | None:
        """Выписка запуска: папка результата или statement.json; предупреждения — из extraction_report.json рядом.

        Нет файла — None, файл не той формы — domain.EvaluationFileInvalid.
        """
        ...

    async def read_reference_statement(self, path: str) -> domain.ReferenceStatement | None:
        """Эталонная выписка. Нет файла — None, файл не той формы — domain.EvaluationFileInvalid."""
        ...


@dataclass
class Usecase:
    bank: Bank
    client_window: ClientWindow
    storage: ResultStorage

    # Statement
    extract_statement = extract_statement


@dataclass
class EvaluationUsecase:
    """Сценарии оценки качества: не требуют банка, браузера и настроек извлечения (ADR 0005)."""

    statement_files: StatementFiles

    evaluate_statement = evaluate_statement
