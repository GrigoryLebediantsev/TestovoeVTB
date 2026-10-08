from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Playwright, sync_playwright

from tests.e2e_support import ClientBrowser, DemoBankServer, start_client_chromium


@pytest.fixture(scope='session')
def demo_bank_server() -> Iterator[DemoBankServer]:
    server = DemoBankServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def demo_bank(demo_bank_server: DemoBankServer) -> DemoBankServer:
    """Чистое состояние демо-банка перед каждым тестом."""
    demo_bank_server.set_mode('normal')
    return demo_bank_server


@pytest.fixture(scope='session')
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as playwright_instance:
        yield playwright_instance


@pytest.fixture
def client_browser(playwright: Playwright, tmp_path: Path) -> Iterator[ClientBrowser]:
    process, cdp_url = start_client_chromium(playwright.chromium.executable_path, tmp_path / 'client-profile')
    browser = playwright.chromium.connect_over_cdp(cdp_url)
    yield ClientBrowser(cdp_url=cdp_url, context=browser.contexts[0])
    browser.close()
    process.terminate()
    process.wait(timeout=10)
