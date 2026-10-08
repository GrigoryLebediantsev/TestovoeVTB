"""Демо без окна: весь сценарий прототипа на демо-банке, действия клиента выполняет скрипт.

Поднимает демо-банк и Chromium без окна, запускает прототип в режиме cdp, в браузере даёт согласие
и входит в кабинет (demo / demo, код 0000), затем печатает итоговую страницу и оценку качества выписки.
Код завершения — код прототипа: 0 — всё полно, 2 — есть предупреждения, 1 — выписка не сформирована.
"""

import argparse
import tempfile
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright

from demo_bank.app import DemoBankMode
from src.adapter.browser_window import FAILURE_PAGE_TITLE, SUMMARY_PAGE_TITLE
from tests.e2e_support import (
    EXIT_FAILED,
    DemoBankServer,
    find_page_with_title,
    finish_program,
    give_consent_and_log_in,
    open_client_browser,
    run_program,
    start_program,
)

# Цветной вывод лога вместо JSON: демо читает человек
DEMO_ENV = {'LOGGER__PRETTY_CONSOLE': 'true'}


def main() -> int:
    parser = argparse.ArgumentParser(prog='python -m scripts.headless_demo', description=__doc__.splitlines()[0])
    parser.add_argument('--mode', type=DemoBankMode, choices=list(DemoBankMode), default=DemoBankMode.NORMAL)
    parser.add_argument('--output', default='output', help='Папка результатов (по умолчанию output)')
    arguments = parser.parse_args()
    output_dir = Path(arguments.output).resolve()

    demo_bank = DemoBankServer()
    demo_bank.start()
    try:
        demo_bank.set_mode(arguments.mode)
        with tempfile.TemporaryDirectory(prefix='headless-demo-') as work_dir:
            return _run_demo(demo_bank, arguments.mode, Path(work_dir), output_dir)
    finally:
        demo_bank.stop()


def _run_demo(demo_bank: DemoBankServer, mode: DemoBankMode, work_dir: Path, output_dir: Path) -> int:
    folders_before = _list_run_folders(output_dir)
    print(f'Демо-банк: {demo_bank.base_url}, режим {mode}', flush=True)
    with sync_playwright() as playwright, open_client_browser(playwright, work_dir / 'profile') as client_browser:
        env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir) | DEMO_ENV
        process = start_program(env, work_dir)
        give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
        result = finish_program(process)
        print(result.output, flush=True)
        _print_result_page(client_browser.context)

    if result.returncode != EXIT_FAILED:
        _print_evaluation(_list_run_folders(output_dir) - folders_before, work_dir)
    return result.returncode


def _print_evaluation(new_folders: set[Path], work_dir: Path) -> None:
    """Оценка качества новой выписки по эталонной демо-банка."""
    if len(new_folders) != 1:
        print(f'Оценка качества пропущена: ожидалась одна новая папка, найдено {len(new_folders)}', flush=True)
        return
    print('Оценка качества по эталонной выписке:', flush=True)
    evaluation = run_program({}, work_dir, arguments=['evaluate', str(new_folders.pop())])
    print(evaluation.output, flush=True)


def _list_run_folders(output_dir: Path) -> set[Path]:
    return set(output_dir.iterdir()) if output_dir.exists() else set()


def _print_result_page(context: BrowserContext) -> None:
    """Текст итоговой страницы прототипа — то, что клиент видит в браузере."""
    for title in (SUMMARY_PAGE_TITLE, FAILURE_PAGE_TITLE):
        page = find_page_with_title(context, title)
        if page is not None:
            print('Страница в браузере клиента:', flush=True)
            print(page.inner_text('body'), flush=True)
            return


if __name__ == '__main__':
    raise SystemExit(main())
