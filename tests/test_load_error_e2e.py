from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    extract_statement,
    find_sensitive_values,
)

# История карты и страница кредита отвечают ошибкой сервера: оба продукта не извлечены,
# остальные — как в обычном режиме
EXPECTED_PRODUCT_REPORTS = [
    {
        'product_id': 'acc-rub',
        'masked_number': '**** 4567',
        'status': 'complete',
        'extraction_source': 'export',
        'transactions_count': 9,
        'reason': None,
    },
    {
        'product_id': 'acc-usd',
        'masked_number': '**** 4321',
        'status': 'complete',
        'extraction_source': 'server_response',
        'transactions_count': 12,
        'reason': None,
    },
    {
        'product_id': 'card-debit',
        'masked_number': '**** 9012',
        'status': 'failed',
        'extraction_source': None,
        'transactions_count': 0,
        'reason': 'история операций не загружена',
    },
    {
        'product_id': 'savings',
        'masked_number': '**** 1234',
        'status': 'complete',
        'extraction_source': 'page',
        'transactions_count': 7,
        'reason': None,
    },
    {
        'product_id': 'loan',
        'masked_number': None,
        'status': 'failed',
        'extraction_source': None,
        'transactions_count': 0,
        'reason': 'карточка продукта не загружена',
    },
]
EXPECTED_ERRORS = [
    'Продукт card-debit: история операций не загружена',
    'Продукт loan: карточка продукта не загружена',
]
# Карта без операций остаётся в выписке, кредит без карточки — нет
EXPECTED_STATEMENT_PRODUCT_IDS = ['acc-rub', 'acc-usd', 'card-debit', 'savings']
EXPECTED_TRANSACTIONS_COUNT = 28


def test_load_error_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    demo_bank.set_mode('load_error')

    run = extract_statement(demo_bank, client_browser, tmp_path / 'run')

    assert run.result.returncode == EXIT_WITH_WARNINGS, run.result.output
    statement = run.read_json('statement.json')
    assert [product['product_id'] for product in statement['products']] == EXPECTED_STATEMENT_PRODUCT_IDS
    assert [item for item in statement['transactions'] if item['product_id'] == 'card-debit'] == []
    assert len(statement['transactions']) == EXPECTED_TRANSACTIONS_COUNT

    report = run.read_json('extraction_report.json')
    assert report['products'] == EXPECTED_PRODUCT_REPORTS
    assert report['errors'] == EXPECTED_ERRORS
    assert report['transactions_count'] == EXPECTED_TRANSACTIONS_COUNT
    assert report['products_count'] == len(EXPECTED_STATEMENT_PRODUCT_IDS)

    report_text = (run.run_folder / 'extraction_report.json').read_text(encoding='utf-8')
    assert find_sensitive_values(run.result.output + report_text) == []
