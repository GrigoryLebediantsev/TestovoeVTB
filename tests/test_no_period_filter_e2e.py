from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    NORMAL_MODE_TRANSACTIONS_COUNT,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
)

# Без фильтра кабинет отдаёт всю историю: у каждого продукта с операциями одна лишняя — до начала периода
EXPECTED_WARNINGS = [
    'Продукт acc-rub: фильтр периода в кабинете не найден',
    'Продукт acc-rub: отброшено операций вне периода: 1',
    'Продукт acc-usd: фильтр периода в кабинете не найден',
    'Продукт acc-usd: отброшено операций вне периода: 1',
    'Продукт card-debit: фильтр периода в кабинете не найден',
    'Продукт card-debit: отброшено операций вне периода: 1',
    'Продукт savings: фильтр периода в кабинете не найден',
    'Продукт savings: отброшено операций вне периода: 1',
    'Продукт loan: фильтр периода в кабинете не найден',
]


def test_no_period_filter_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    demo_bank.set_mode('no_period_filter')

    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')

    assert run.result.returncode == EXIT_WITH_WARNINGS, run.result.output
    report = run.read_json('extraction_report.json')
    for expected_warning in EXPECTED_WARNINGS:
        assert expected_warning in report['warnings']
    assert report['errors'] == []

    # Лишнее отброшено: выписка та же, что и с фильтром
    statement = run.read_json('statement.json')
    assert len(statement['transactions']) == NORMAL_MODE_TRANSACTIONS_COUNT
    assert report['transactions_count'] == NORMAL_MODE_TRANSACTIONS_COUNT
