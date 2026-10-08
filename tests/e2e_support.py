import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, expect

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRAM_TIMEOUT_SECONDS = 120
STARTUP_TIMEOUT_SECONDS = 20
CLIENT_ACTION_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 0.1

DEMO_LOGIN = 'demo'
DEMO_PASSWORD = 'demo'
DEMO_ONE_TIME_CODE = '0000'

# Код завершения: выписка сохранена, есть предупреждения. В обычном режиме демо-банка они есть всегда:
# дубликаты операций карты и операции вне периода
EXIT_WITH_WARNINGS = 2


@dataclass
class ProgramResult:
    returncode: int
    output: str


@dataclass
class ClientBrowser:
    """Chrome клиента: запущен с портом отладки, тест управляет им через свой Playwright."""

    cdp_url: str
    context: BrowserContext


def wait_for[T](condition: Callable[[], T | None], timeout: float, description: str) -> T:
    """Опрашивает условие до таймаута и возвращает первый непустой результат."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f'Timed out waiting for {description}')


def find_free_port() -> int:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port: int = probe.getsockname()[1]
        return port


def is_url_available(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1):
            return True
    except urllib.error.URLError, ConnectionError, TimeoutError:
        return False


def post_json(url: str, payload: dict[str, str]) -> None:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST'
    )
    with urllib.request.urlopen(request, timeout=5):
        pass


# --- Демо-банк ---


class DemoBankServer:
    def __init__(self) -> None:
        self.port = find_free_port()
        self.base_url = f'http://127.0.0.1:{self.port}'
        self._process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self._process = subprocess.Popen(
            [sys.executable, '-m', 'demo_bank', '--port', str(self.port)],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_for(lambda: is_url_available(f'{self.base_url}/_test/health'), STARTUP_TIMEOUT_SECONDS, 'demo bank')

    def stop(self) -> None:
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=10)

    def set_mode(self, mode: str) -> None:
        """Переключает режим и сбрасывает сессии входа."""
        post_json(f'{self.base_url}/_test/mode', {'mode': mode})

    def get_api_calls(self) -> list[dict[str, object]]:
        """Запросы порций истории к серверу банка, записанные демо-банком."""
        with urllib.request.urlopen(f'{self.base_url}/_test/api-calls', timeout=5) as response:
            api_calls: list[dict[str, object]] = json.loads(response.read())
            return api_calls

    def program_env(self, client_browser_cdp_url: str, output_dir: Path) -> dict[str, str]:
        return {
            'EXTRACTION__BANK': 'demo_bank',
            'EXTRACTION__PERIOD_FROM': '2026-05-01',
            'EXTRACTION__PERIOD_TO': '2026-06-30',
            'DEMO_BANK__BASE_URL': self.base_url,
            'BROWSER__MODE': 'cdp',
            'BROWSER__CDP_URL': client_browser_cdp_url,
            'STORAGE__OUTPUT_DIR': str(output_dir),
            'LOGGER__PRETTY_CONSOLE': 'false',
        }


# --- Браузер клиента ---


def start_client_chromium(executable_path: str, profile_dir: Path) -> tuple[subprocess.Popen[bytes], str]:
    port = find_free_port()
    process = subprocess.Popen(
        [
            executable_path,
            '--headless=new',
            f'--remote-debugging-port={port}',
            f'--user-data-dir={profile_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            'about:blank',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cdp_url = f'http://127.0.0.1:{port}'
    wait_for(lambda: is_url_available(f'{cdp_url}/json/version'), STARTUP_TIMEOUT_SECONDS, 'client chromium')
    return process, cdp_url


def find_page_with_button(context: BrowserContext, button_name: str) -> Page | None:
    for page in context.pages:
        try:
            if page.get_by_role('button', name=button_name).count() > 0:
                return page
        except Exception:
            # Страница могла закрыться или перейти по адресу во время проверки
            continue
    return None


def give_consent_and_log_in(context: BrowserContext, expected_consent_texts: list[str]) -> Page:
    """Действия клиента: согласие во вкладке прототипа и самостоятельный вход в кабинет."""
    page = wait_for(lambda: find_page_with_button(context, 'Разрешаю'), CLIENT_ACTION_TIMEOUT_SECONDS, 'consent page')
    for expected_text in expected_consent_texts:
        expect(page.get_by_text(expected_text).first).to_be_visible()
    page.get_by_role('button', name='Разрешаю').click()

    page.get_by_label('Логин').fill(DEMO_LOGIN, timeout=CLIENT_ACTION_TIMEOUT_SECONDS * 1000)
    page.get_by_label('Пароль').fill(DEMO_PASSWORD)
    page.get_by_role('button', name='Войти').click()

    page.get_by_label('Код из СМС').fill(DEMO_ONE_TIME_CODE, timeout=CLIENT_ACTION_TIMEOUT_SECONDS * 1000)
    page.get_by_role('button', name='Подтвердить').click()
    return page


# --- Прототип ---


def program_environment(env: dict[str, str]) -> dict[str, str]:
    """Чистое окружение: только системные пути и явно заданные настройки."""
    return {'PATH': os.environ['PATH'], 'PYTHONPATH': str(REPO_ROOT), **env}


def start_program(env: dict[str, str], work_dir: Path) -> subprocess.Popen[str]:
    """Запуск прототипа так же, как из командной строки; рабочая папка без .env."""
    return subprocess.Popen(
        [sys.executable, '-m', 'src.main'],
        cwd=work_dir,
        env=program_environment(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def finish_program(process: subprocess.Popen[str]) -> ProgramResult:
    output, _ = process.communicate(timeout=PROGRAM_TIMEOUT_SECONDS)
    return ProgramResult(returncode=process.returncode, output=output)


def run_program(env: dict[str, str], work_dir: Path) -> ProgramResult:
    return finish_program(start_program(env, work_dir))
