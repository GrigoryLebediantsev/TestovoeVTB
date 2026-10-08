import argparse
import logging

from src import deps, domain, dto

log = logging.getLogger(__name__)

EXIT_COMPLETE = 0
EXIT_FAILED = 1
EXIT_WITH_WARNINGS = 2  # выписка сохранена, но есть предупреждения, ошибки или пропуски


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog='python -m src.main',
        description='Извлечение комплексной банковской выписки после входа клиента в личный кабинет',
    )


async def run(arguments: list[str], default_input: dto.ExtractStatementInput) -> int:
    build_parser().parse_args(arguments)
    try:
        result = await deps.get_usecase().extract_statement(default_input)
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
