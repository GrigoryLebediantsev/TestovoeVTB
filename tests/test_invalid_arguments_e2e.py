from pathlib import Path

import pytest

from tests.e2e_support import DEMO_PERIOD_FROM, DEMO_PERIOD_TO, EXIT_FAILED, run_program

# Браузер и демо-банк не нужны: неверные параметры отклоняются до открытия браузера
VALID_ENV = {
    'EXTRACTION__BANK': 'demo_bank',
    'EXTRACTION__PERIOD_FROM': DEMO_PERIOD_FROM,
    'EXTRACTION__PERIOD_TO': DEMO_PERIOD_TO,
    'DEMO_BANK__BASE_URL': 'http://127.0.0.1:9',
    'BROWSER__MODE': 'cdp',
    'BROWSER__CDP_URL': 'http://127.0.0.1:9',
    'LOGGER__PRETTY_CONSOLE': 'false',
}


@pytest.mark.parametrize(
    ('arguments', 'env_override', 'expected_message'),
    [
        (['--from', '01.06.2026'], {}, 'Неверные параметры запуска'),
        (['--from', '2026-07-01'], {}, 'Начало периода позже конца'),
        ([], {'EXTRACTION__PERIOD_FROM': '2026-07-01'}, 'Начало периода позже конца'),
        (['--unknown'], {}, 'Неверные параметры запуска'),
    ],
    ids=['not a date', 'from after to', 'env from after to', 'unknown argument'],
)
def test_invalid_arguments_flow(
    arguments: list[str], env_override: dict[str, str], expected_message: str, tmp_path: Path
) -> None:
    result = run_program(VALID_ENV | env_override, tmp_path, arguments)

    assert result.returncode == EXIT_FAILED, result.output
    assert expected_message in result.output
    # До браузера дело не дошло: иначе была бы ошибка подключения к нему
    assert 'Browser not available' not in result.output
