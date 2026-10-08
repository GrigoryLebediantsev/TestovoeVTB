import json
from pathlib import Path

from tests.e2e_support import (
    EXIT_COMPLETE,
    EXIT_FAILED,
    NORMAL_MODE_TRANSACTIONS_COUNT,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
    run_program,
)

# Оценке .env не нужен: запускаем с пустым окружением
NO_SETTINGS: dict[str, str] = {}
JULY_STATEMENT = {'period': {'from': '2026-07-01', 'to': '2026-07-31'}, 'transactions': []}


def test_evaluate_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')
    warnings_count = len(run.read_json('extraction_report.json')['warnings'])

    # Путь — папка результата или сам statement.json
    for statement_path in (run.run_folder, run.run_folder / 'statement.json'):
        result = run_program(NO_SETTINGS, tmp_path, arguments=['evaluate', str(statement_path)])

        assert result.returncode == EXIT_COMPLETE, result.output
        assert (
            f'Операций в выписке: {NORMAL_MODE_TRANSACTIONS_COUNT}, в эталоне: {NORMAL_MODE_TRANSACTIONS_COUNT}, '
            f'совпало: {NORMAL_MODE_TRANSACTIONS_COUNT}'
        ) in result.output
        assert 'Точность (precision): 1.000' in result.output
        assert 'Полнота (recall): 1.000' in result.output
        assert 'Доля нормализованных полей: 1.000' in result.output
        assert f'Предупреждений: {warnings_count}' in result.output


def test_evaluate_missing_file_flow(tmp_path: Path) -> None:
    missing_path = str(tmp_path / 'missing')

    result = run_program(NO_SETTINGS, tmp_path, arguments=['evaluate', missing_path])

    assert result.returncode == EXIT_FAILED, result.output
    assert f'Оценка не выполнена: Файл не найден: {missing_path}' in result.output


def test_evaluate_empty_folder_flow(tmp_path: Path) -> None:
    empty_folder = tmp_path / 'run'
    empty_folder.mkdir()

    result = run_program(NO_SETTINGS, tmp_path, arguments=['evaluate', str(empty_folder)])

    assert result.returncode == EXIT_FAILED, result.output
    # В сообщении путь, который ввёл человек
    assert result.output.rstrip().endswith(f'Оценка не выполнена: Файл не найден: {empty_folder}')


def test_evaluate_missing_reference_flow(
    demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path
) -> None:
    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')
    missing_reference = str(tmp_path / 'missing_reference.json')

    result = run_program(
        NO_SETTINGS, tmp_path, arguments=['evaluate', str(run.run_folder), '--reference', missing_reference]
    )

    assert result.returncode == EXIT_FAILED, result.output
    assert f'Оценка не выполнена: Файл не найден: {missing_reference}' in result.output


def test_evaluate_period_outside_reference_flow(tmp_path: Path) -> None:
    run_folder = tmp_path / 'run'
    run_folder.mkdir()
    (run_folder / 'statement.json').write_text(json.dumps(JULY_STATEMENT), encoding='utf-8')
    (run_folder / 'extraction_report.json').write_text(json.dumps({'warnings': []}), encoding='utf-8')

    result = run_program(NO_SETTINGS, tmp_path, arguments=['evaluate', str(run_folder)])

    assert result.returncode == EXIT_FAILED, result.output
    assert 'Период выписки выходит за период эталонной выписки' in result.output


def test_evaluate_broken_file_flow(tmp_path: Path) -> None:
    run_folder = tmp_path / 'run'
    run_folder.mkdir()
    (run_folder / 'statement.json').write_text('{"products": []}', encoding='utf-8')
    (run_folder / 'extraction_report.json').write_text(json.dumps({'warnings': []}), encoding='utf-8')

    result = run_program(NO_SETTINGS, tmp_path, arguments=['evaluate', str(run_folder)])

    assert result.returncode == EXIT_FAILED, result.output
    assert 'Оценка не выполнена: Файл не похож на выписку прототипа' in result.output
