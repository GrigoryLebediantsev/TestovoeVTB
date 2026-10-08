from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
    find_sensitive_values,
)


def test_sensitive_data_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')

    assert run.result.returncode == EXIT_WITH_WARNINGS, run.result.output
    # Проверка не пустая: в самой выписке эти значения есть
    statement_text = (run.run_folder / 'statement.json').read_text(encoding='utf-8')
    assert find_sensitive_values(statement_text)

    report_text = (run.run_folder / 'extraction_report.json').read_text(encoding='utf-8')
    assert find_sensitive_values(run.result.output) == []
    assert find_sensitive_values(report_text) == []
