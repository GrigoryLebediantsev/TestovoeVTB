from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
    find_sensitive_values,
)

NORMAL_ACC_USD_TRANSACTIONS_COUNT = 12

# Изменены классы таблицы операций и кнопки «Показать ещё»
EXPECTED_STATUSES = {
    'acc-rub': ('complete', 'export', None),  # экспорт не зависит от таблицы
    'acc-usd': ('partial', 'server_response', 'история загружена не полностью'),  # нет кнопки следующей порции
    'card-debit': ('complete', 'server_response', None),  # подгрузка прокруткой не изменилась
    'savings': ('failed', None, 'разметка истории операций не распознана'),
    'loan': ('complete', 'page', None),  # надпись «Операций нет» осталась прежней
}
EXPECTED_ERRORS = ['Продукт savings: разметка истории операций не распознана']
EXPECTED_WARNING = 'Продукт acc-usd: история загружена не полностью'


def test_changed_layout_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    demo_bank.set_mode('changed_layout')

    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')

    assert run.result.returncode == EXIT_WITH_WARNINGS, run.result.output
    report = run.read_json('extraction_report.json')
    statuses = {
        item['product_id']: (item['status'], item['extraction_source'], item['reason']) for item in report['products']
    }
    assert statuses == EXPECTED_STATUSES
    assert report['errors'] == EXPECTED_ERRORS
    assert EXPECTED_WARNING in report['warnings']

    counts = {item['product_id']: item['transactions_count'] for item in report['products']}
    assert 0 < counts['acc-usd'] < NORMAL_ACC_USD_TRANSACTIONS_COUNT
    assert counts['savings'] == 0

    statement = run.read_json('statement.json')
    assert [item for item in statement['transactions'] if item['product_id'] == 'savings'] == []

    report_text = (run.run_folder / 'extraction_report.json').read_text(encoding='utf-8')
    assert find_sensitive_values(run.result.output + report_text) == []
