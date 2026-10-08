import argparse
import datetime
import logging
from dataclasses import dataclass
from typing import NoReturn

import pydantic

from src import deps, domain, dto

log = logging.getLogger(__name__)

EXIT_COMPLETE = 0
EXIT_FAILED = 1
EXIT_WITH_WARNINGS = 2  # выписка сохранена, но есть предупреждения, ошибки или пропуски


@dataclass
class LaunchDefaults:
    """Параметры запуска из .env; аргументы командной строки переопределяют период."""

    bank: str
    period_from: datetime.date
    period_to: datetime.date
    format: domain.StatementFormat


class InvalidArgumentsError(Exception): ...


class RaisingArgumentParser(argparse.ArgumentParser):
    """Ошибка аргументов — исключение, а не выход с кодом 2: код 2 у прототипа значит «есть предупреждения»."""

    def error(self, message: str) -> NoReturn:
        raise InvalidArgumentsError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = RaisingArgumentParser(
        prog='python -m src.main',
        description='Извлечение комплексной банковской выписки после входа клиента в личный кабинет',
    )
    parser.add_argument(
        '--from', dest='period_from', type=_parse_date, help='Начало периода, ГГГГ-ММ-ДД (по умолчанию из .env)'
    )
    parser.add_argument(
        '--to', dest='period_to', type=_parse_date, help='Конец периода, ГГГГ-ММ-ДД (по умолчанию из .env)'
    )
    return parser


def parse_input(arguments: list[str], defaults: LaunchDefaults) -> dto.ExtractStatementInput | None:
    """Вход сценария: период из аргументов или .env. Неверные параметры — сообщение оператору и None."""
    try:
        parsed = build_parser().parse_args(arguments)
        return dto.ExtractStatementInput(
            bank=defaults.bank,
            period_from=parsed.period_from or defaults.period_from,
            period_to=parsed.period_to or defaults.period_to,
            format=defaults.format,
        )
    except InvalidArgumentsError as error:
        message = str(error)
    except pydantic.ValidationError as error:
        message = _describe_validation_error(error)
    log.error('Invalid launch parameters')
    print(f'Неверные параметры запуска: {message}')
    return None


async def run(extraction_input: dto.ExtractStatementInput) -> int:
    try:
        result = await deps.get_usecase().extract_statement(extraction_input)
    except domain.DomainError as error:
        log.error('Statement not extracted: %s', error)
        print(f'Выписка не сформирована: {error}')
        return EXIT_FAILED
    except Exception:
        log.exception('Statement extraction crashed')
        print('Выписка не сформирована: непредвиденная ошибка, подробности в логе')
        return EXIT_FAILED

    print(f'Выписка сохранена: {result.output_folder}')
    print(f'Продуктов: {result.products_count}')
    print(f'Операций: {result.transactions_count}')
    print(f'Предупреждений: {result.warnings_count}, ошибок: {result.errors_count}')
    return EXIT_COMPLETE if result.is_complete else EXIT_WITH_WARNINGS


def _parse_date(text: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f'ожидается дата ГГГГ-ММ-ДД, получено {text!r}') from error


def _describe_validation_error(error: pydantic.ValidationError) -> str:
    """Тексты ошибок проверки входа; у ошибок валидаторов — исходный текст без префикса pydantic."""
    messages = []
    for detail in error.errors():
        original_error = detail.get('ctx', {}).get('error')
        messages.append(str(original_error) if original_error else detail['msg'])
    return '; '.join(messages)
