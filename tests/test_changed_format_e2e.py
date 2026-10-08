import json
from pathlib import Path
from typing import Any

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    finish_program,
    give_consent_and_log_in,
    start_program,
)

PERIOD_FROM = '2026-05-01'
PERIOD_TO = '2026-06-30'

# В изменённом формате банк переименовал статус этой операции: «Проведена» → «Исполнена»
RENAMED_STATUS_TRANSACTION_ID = 'sv-0003'
UNKNOWN_STATUS_WARNING = 'Продукт savings: незнакомый статус операции «Исполнена»: 1'


def test_changed_format_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    normal_folder = _extract_statement(demo_bank, client_browser, tmp_path / 'normal')
    demo_bank.set_mode('changed_format')
    changed_folder = _extract_statement(demo_bank, client_browser, tmp_path / 'changed')

    normal_statement = _read_json(normal_folder / 'statement.json')
    changed_statement = _read_json(changed_folder / 'statement.json')
    assert changed_statement['products'] == normal_statement['products']
    assert changed_statement['transactions'] == [
        _with_unknown_status_if_renamed(transaction) for transaction in normal_statement['transactions']
    ]

    normal_report = _read_json(normal_folder / 'extraction_report.json')
    changed_report = _read_json(changed_folder / 'extraction_report.json')
    assert changed_report['products'] == normal_report['products']
    assert UNKNOWN_STATUS_WARNING in changed_report['warnings']
    assert [warning for warning in changed_report['warnings'] if warning != UNKNOWN_STATUS_WARNING] == normal_report[
        'warnings'
    ]
    assert changed_report['errors'] == []


def _extract_statement(demo_bank: DemoBankServer, client_browser: ClientBrowser, work_dir: Path) -> Path:
    """Один запуск прототипа; возвращает папку с результатом."""
    work_dir.mkdir()
    output_dir = work_dir / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(
        env | {'EXTRACTION__PERIOD_FROM': PERIOD_FROM, 'EXTRACTION__PERIOD_TO': PERIOD_TO}, work_dir
    )

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    return run_folder


def _with_unknown_status_if_renamed(transaction: dict[str, object]) -> dict[str, object]:
    if transaction['transaction_id'] == RENAMED_STATUS_TRANSACTION_ID:
        return transaction | {'status': 'unknown'}
    return transaction


def _read_json(path: Path) -> dict[str, Any]:
    content: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
    return content
