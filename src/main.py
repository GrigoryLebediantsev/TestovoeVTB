import asyncio
import logging
import sys

from shared import logger
from src import deps, dto
from src.adapter.browser_window import BrowserWindow
from src.adapter.demo_bank import DemoBank
from src.adapter.file_storage import FileStorage
from src.config import BankName, settings
from src.controller import cli
from src.usecase import Bank, Usecase

log = logging.getLogger(__name__)


async def run_application(arguments: list[str]) -> int:
    try:
        await browser_window.connect()
    except Exception:
        log.exception('Browser not available')
        return cli.EXIT_FAILED

    try:
        return await cli.run(arguments, default_input)
    finally:
        await browser_window.close()


def create_bank(bank_name: BankName, window: BrowserWindow) -> Bank:
    match bank_name:
        case BankName.DEMO_BANK:
            return DemoBank(settings.demo_bank, window)


logger.init(settings.logger)

browser_window = BrowserWindow(settings.browser)
storage = FileStorage(settings.storage)
usecase = Usecase(
    bank=create_bank(settings.extraction.BANK, browser_window), client_window=browser_window, storage=storage
)
deps.set_usecase(usecase)

default_input = dto.ExtractStatementInput(
    bank=settings.extraction.BANK,
    period_from=settings.extraction.PERIOD_FROM,
    period_to=settings.extraction.PERIOD_TO,
    format=settings.storage.FORMAT,
)


def main() -> None:
    sys.exit(asyncio.run(run_application(sys.argv[1:])))


if __name__ == '__main__':
    main()
