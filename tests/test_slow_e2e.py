from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
    find_sensitive_values,
)

# Таймаут меньше задержки первого запроса истории карты в режиме slow (5 с): первая попытка падает, повтор успешен
SLOW_ENV = {'DEMO_BANK__ACTION_TIMEOUT_SECONDS': '2', 'DEMO_BANK__RETRY_COUNT': '2'}
RETRY_WARNING = 'Продукт card-debit: история загружена после повторной попытки'


def test_slow_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    normal_run = extract_statement(demo_bank, client_browser, tmp_path / 'normal')
    demo_bank.set_mode('slow')
    slow_run = extract_statement(demo_bank, client_browser, tmp_path / 'slow', extra_env=SLOW_ENV)

    assert slow_run.result.returncode == EXIT_WITH_WARNINGS, slow_run.result.output
    normal_statement = normal_run.read_json('statement.json')
    slow_statement = slow_run.read_json('statement.json')
    assert slow_statement['products'] == normal_statement['products']
    assert slow_statement['transactions'] == normal_statement['transactions']

    normal_report = normal_run.read_json('extraction_report.json')
    slow_report = slow_run.read_json('extraction_report.json')
    assert slow_report['products'] == normal_report['products']
    assert slow_report['errors'] == []
    assert RETRY_WARNING in slow_report['warnings']
    assert [warning for warning in slow_report['warnings'] if warning != RETRY_WARNING] == normal_report['warnings']
    report_text = (slow_run.run_folder / 'extraction_report.json').read_text(encoding='utf-8')
    assert find_sensitive_values(slow_run.result.output + report_text) == []
