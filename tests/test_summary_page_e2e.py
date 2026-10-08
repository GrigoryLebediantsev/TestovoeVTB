import json
from pathlib import Path
from typing import Any

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    find_sensitive_values,
    finish_program,
    give_consent_and_log_in,
    read_page_text,
    start_program,
)

SUMMARY_PAGE_TITLE = 'Выписка сформирована'
# Период в .env — май–июнь, аргументы сужают его до июня
PERIOD_ARGUMENTS = ['--from', '2026-06-01', '--to', '2026-06-30']
EXPECTED_PERIOD = {'from': '2026-06-01', 'to': '2026-06-30'}
EXPECTED_PERIOD_TEXT = '01.06.2026 — 30.06.2026'


def test_summary_page_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env, tmp_path, arguments=PERIOD_ARGUMENTS)

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[EXPECTED_PERIOD_TEXT])
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    report = _read_report(run_folder)
    assert report['period'] == EXPECTED_PERIOD

    # Вкладка в режиме CDP остаётся открытой с итоговой страницей
    summary_text = read_page_text(client_browser.context, SUMMARY_PAGE_TITLE)
    assert 'Демо-банк' in summary_text
    assert EXPECTED_PERIOD_TEXT in summary_text
    assert f'Продуктов: {report["products_count"]}' in summary_text
    assert f'Операций: {report["transactions_count"]}' in summary_text
    assert report['warnings']
    for warning in report['warnings']:
        assert warning in summary_text
    assert find_sensitive_values(summary_text) == []


def _read_report(run_folder: Path) -> dict[str, Any]:
    report: dict[str, Any] = json.loads((run_folder / 'extraction_report.json').read_text(encoding='utf-8'))
    return report
