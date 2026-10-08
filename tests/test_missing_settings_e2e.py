from pathlib import Path

from tests.e2e_support import run_program

REQUIRED_SETTINGS = [
    'EXTRACTION__BANK',
    'EXTRACTION__PERIOD_FROM',
    'EXTRACTION__PERIOD_TO',
    'DEMO_BANK__BASE_URL',
]


def test_missing_settings_flow(tmp_path: Path) -> None:
    result = run_program(env={}, work_dir=tmp_path)

    assert result.returncode == 1
    for setting_name in REQUIRED_SETTINGS:
        assert setting_name in result.output
