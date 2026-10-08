from pathlib import Path

from tests.e2e_support import (
    CLIENT_ACTION_TIMEOUT_SECONDS,
    EXIT_FAILED,
    FAILURE_PAGE_TITLE,
    ClientBrowser,
    DemoBankServer,
    find_page_with_button,
    finish_program,
    read_page_text,
    start_program,
    wait_for,
)

LOGIN_TIMEOUT_REASON = 'Клиент не вошёл в личный кабинет за отведённое время'
SHORT_LOGIN_TIMEOUT = {'DEMO_BANK__LOGIN_TIMEOUT_SECONDS': '2'}


def test_login_timeout_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env | SHORT_LOGIN_TIMEOUT, tmp_path)

    # Клиент соглашается, но в кабинет не входит
    consent_page = wait_for(
        lambda: find_page_with_button(client_browser.context, 'Разрешаю'),
        CLIENT_ACTION_TIMEOUT_SECONDS,
        'consent page',
    )
    consent_page.get_by_role('button', name='Разрешаю').click()
    result = finish_program(process)

    assert result.returncode == EXIT_FAILED, result.output
    assert LOGIN_TIMEOUT_REASON in result.output
    assert not output_dir.exists()
    assert demo_bank.get_api_calls() == []
    assert LOGIN_TIMEOUT_REASON in read_page_text(client_browser.context, FAILURE_PAGE_TITLE)
