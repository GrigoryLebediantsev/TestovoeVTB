import os
import subprocess
import sys
from pathlib import Path

from src.adapter.browser_window import SUMMARY_PAGE_TITLE
from tests.e2e_support import EXIT_WITH_WARNINGS, PROGRAM_TIMEOUT_SECONDS, REPO_ROOT

SAVED_TEXT = 'Выписка сохранена'
FULL_RECALL_TEXT = 'Полнота (recall): 1.000'


def test_headless_demo_flow(tmp_path: Path) -> None:
    output_dir = tmp_path / 'output'

    result = subprocess.run(
        [sys.executable, '-m', 'scripts.headless_demo', '--output', str(output_dir)],
        cwd=tmp_path,
        # Окружение не очищаем: скрипту нужен путь к браузерам Playwright, прототип он сам запускает с чистым
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=PROGRAM_TIMEOUT_SECONDS,
    )
    output = result.stdout + result.stderr

    # В обычном режиме демо-банка всегда есть предупреждения: дубликаты операций карты и операции вне периода
    assert result.returncode == EXIT_WITH_WARNINGS, output
    assert SAVED_TEXT in output
    # Текст итоговой страницы, которую клиент видит в браузере
    assert SUMMARY_PAGE_TITLE in output
    assert FULL_RECALL_TEXT in output
    assert len(list(output_dir.iterdir())) == 1
