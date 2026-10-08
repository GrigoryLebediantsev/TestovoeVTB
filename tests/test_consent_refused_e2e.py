from pathlib import Path

from tests.e2e_support import (
    CLIENT_ACTION_TIMEOUT_SECONDS,
    EXIT_FAILED,
    ClientBrowser,
    DemoBankServer,
    find_page_with_button,
    finish_program,
    read_page_text,
    start_program,
    wait_for,
)

FAILURE_PAGE_TITLE = 'Выписка не сформирована'
REFUSAL_REASON = 'Клиент отказался от чтения данных'


def test_consent_refused_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env, tmp_path)

    consent_page = wait_for(
        lambda: find_page_with_button(client_browser.context, 'Отказываюсь'),
        CLIENT_ACTION_TIMEOUT_SECONDS,
        'consent page',
    )
    consent_page.get_by_role('button', name='Отказываюсь').click()
    result = finish_program(process)

    assert result.returncode == EXIT_FAILED, result.output
    assert REFUSAL_REASON in result.output
    # Ничего не прочитано: кабинет банка не открывался, файлов нет
    assert not output_dir.exists()
    assert demo_bank.get_api_calls() == []
    assert all(demo_bank.base_url not in page.url for page in client_browser.context.pages)
    assert REFUSAL_REASON in read_page_text(client_browser.context, FAILURE_PAGE_TITLE)
