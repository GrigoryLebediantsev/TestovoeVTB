from pathlib import Path

from tests.e2e_support import EXIT_COMPLETE, ClientBrowser, DemoBankServer, extract_statement

EXPECTED_PRODUCT_IDS = ['acc-rub', 'acc-usd', 'card-debit', 'savings', 'loan']


def test_empty_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    demo_bank.set_mode('empty')

    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')

    # Пустая история — не ошибка: выписка полная, без предупреждений
    assert run.result.returncode == EXIT_COMPLETE, run.result.output
    statement = run.read_json('statement.json')
    assert [product['product_id'] for product in statement['products']] == EXPECTED_PRODUCT_IDS
    assert statement['transactions'] == []

    report = run.read_json('extraction_report.json')
    assert report['transactions_count'] == 0
    assert report['warnings'] == []
    assert report['errors'] == []
    assert [(item['product_id'], item['status'], item['transactions_count']) for item in report['products']] == [
        (product_id, 'complete', 0) for product_id in EXPECTED_PRODUCT_IDS
    ]
