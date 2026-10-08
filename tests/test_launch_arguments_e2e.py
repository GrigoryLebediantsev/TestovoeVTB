from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    finish_program,
    give_consent_and_log_in,
    start_program,
)

# В .env — JSON и лог только ошибок, аргументы командной строки важнее
ENV_SETTINGS = {'EXTRACTION__FORMAT': 'json', 'LOGGER__LEVEL': 'ERROR'}
LAUNCH_ARGUMENTS = ['--format', 'csv', '--log-level', 'INFO']
EXPECTED_FILES = ['extraction_report.json', 'products.csv', 'transactions.csv']
INFO_LOG_TEXT = '"level": "INFO"'


def test_launch_arguments_override_env_flow(
    demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path
) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env | ENV_SETTINGS, tmp_path, LAUNCH_ARGUMENTS)

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    assert sorted(path.name for path in run_folder.iterdir()) == EXPECTED_FILES
    # С уровнем ERROR из .env сообщений INFO в выводе не было бы
    assert INFO_LOG_TEXT in result.output
