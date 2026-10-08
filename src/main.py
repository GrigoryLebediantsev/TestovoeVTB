import asyncio
import logging
import sys
from pathlib import Path

from shared import logger
from shared.config_helper import load_settings
from shared.logger import LoggerConfig
from src import deps
from src.adapter.browser_window import BrowserWindow
from src.adapter.demo_bank import DemoBank
from src.adapter.file_storage import FileStorage
from src.adapter.json_statement_files import JsonStatementFiles
from src.config import BankName, Settings
from src.controller import cli
from src.usecase import Bank, EvaluationUsecase, Usecase

log = logging.getLogger(__name__)

REFERENCE_STATEMENT_PATH = Path(__file__).resolve().parent.parent / 'demo_bank' / 'reference_statement.json'


async def run_extraction(arguments: list[str]) -> int:
    # Настройки читаются только для извлечения: оценке готовой выписки .env не нужен (ADR 0005)
    settings = load_settings(Settings)
    logger.init(settings.logger)

    # Параметры проверяются до открытия браузера: при ошибке клиент не видит страницу согласия
    launch_defaults = cli.LaunchDefaults(
        bank=settings.extraction.BANK,
        period_from=settings.extraction.PERIOD_FROM,
        period_to=settings.extraction.PERIOD_TO,
        format=settings.storage.FORMAT,
    )
    extraction_input = cli.parse_input(arguments, launch_defaults)
    if extraction_input is None:
        return cli.EXIT_FAILED

    browser_window = BrowserWindow(settings.browser)
    usecase = Usecase(
        bank=create_bank(settings, browser_window),
        client_window=browser_window,
        storage=FileStorage(settings.storage),
    )
    deps.set_usecase(usecase)

    try:
        await browser_window.connect()
    except Exception:
        log.exception('Browser not available')
        return cli.EXIT_FAILED

    try:
        return await cli.run(extraction_input)
    finally:
        await browser_window.close()


async def run_evaluation(arguments: list[str]) -> int:
    logger.init(LoggerConfig())
    evaluation_input = cli.parse_evaluate_input(arguments, default_reference_path=str(REFERENCE_STATEMENT_PATH))
    if evaluation_input is None:
        return cli.EXIT_FAILED

    deps.set_evaluation_usecase(EvaluationUsecase(statement_files=JsonStatementFiles()))
    return await cli.run_evaluation(evaluation_input)


def create_bank(settings: Settings, window: BrowserWindow) -> Bank:
    match settings.extraction.BANK:
        case BankName.DEMO_BANK:
            return DemoBank(settings.demo_bank, window)


def main() -> None:
    arguments = sys.argv[1:]
    if cli.is_evaluate_command(arguments):
        sys.exit(asyncio.run(run_evaluation(arguments[1:])))
    sys.exit(asyncio.run(run_extraction(arguments)))


if __name__ == '__main__':
    main()
