import csv
import json
from pathlib import Path

import pytest

from tests.e2e_support import (
    DEMO_PERIOD_FROM,
    DEMO_PERIOD_TO,
    EXIT_WITH_WARNINGS,
    NORMAL_MODE_TRANSACTIONS_COUNT,
    ClientBrowser,
    DemoBankServer,
    finish_program,
    give_consent_and_log_in,
    start_program,
)

EXPECTED_FILES_BY_FORMAT = {
    'json': ['extraction_report.json', 'statement.json'],
    'csv': ['extraction_report.json', 'products.csv', 'transactions.csv'],
    'both': ['extraction_report.json', 'products.csv', 'statement.json', 'transactions.csv'],
}

EXPECTED_PRODUCT_COLUMNS = [
    'product_id',
    'type',
    'name',
    'masked_number',
    'currency',
    'balance',
    'available_balance',
    'linked_account_id',
    'requisites_account_number',
    'requisites_bic',
    'requisites_correspondent_account',
    'requisites_bank_name',
    'details_interest_rate',
    'details_opened_at',
    'details_credit_limit',
    'details_debt',
]
EXPECTED_TRANSACTION_COLUMNS = [
    'transaction_id',
    'id_source',
    'product_id',
    'operation_date',
    'posting_date',
    'amount',
    'currency',
    'type',
    'description',
    'counterparty',
    'category',
    'status',
    'is_duplicate',
]

# Пустое значение — пустая ячейка, суммы с точкой и двумя знаками, даты ISO
EXPECTED_PRODUCT_ROWS = {
    'acc-rub': {
        'product_id': 'acc-rub',
        'type': 'account',
        'name': 'Текущий счёт',
        'masked_number': '**** 4567',
        'currency': 'RUB',
        'balance': '125430.50',
        'available_balance': '125430.50',
        'linked_account_id': '',
        'requisites_account_number': '40817810500001234567',
        'requisites_bic': '044525999',
        'requisites_correspondent_account': '30101810400000000999',
        'requisites_bank_name': 'АО «Демо-банк»',
        'details_interest_rate': '',
        'details_opened_at': '2021-03-15',
        'details_credit_limit': '',
        'details_debt': '',
    },
    'card-debit': {
        'product_id': 'card-debit',
        'type': 'card',
        'name': 'Дебетовая карта',
        'masked_number': '**** 9012',
        'currency': 'RUB',
        'balance': '125430.50',
        'available_balance': '120430.50',
        'linked_account_id': 'acc-rub',
        'requisites_account_number': '',
        'requisites_bic': '',
        'requisites_correspondent_account': '',
        'requisites_bank_name': '',
        'details_interest_rate': '',
        'details_opened_at': '2021-03-20',
        'details_credit_limit': '',
        'details_debt': '',
    },
    'loan': {
        'product_id': 'loan',
        'type': 'loan',
        'name': 'Потребительский кредит',
        'masked_number': '**** 3322',
        'currency': 'RUB',
        'balance': '',
        'available_balance': '',
        'linked_account_id': '',
        'requisites_account_number': '45507810300004443322',
        'requisites_bic': '044525999',
        'requisites_correspondent_account': '30101810400000000999',
        'requisites_bank_name': 'АО «Демо-банк»',
        'details_interest_rate': '21.9',
        'details_opened_at': '2025-02-01',
        'details_credit_limit': '',
        'details_debt': '230000.00',
    },
}
EXPECTED_TRANSACTION_ROWS = {
    'u-002': {
        'transaction_id': 'u-002',
        'id_source': 'bank',
        'product_id': 'acc-usd',
        'operation_date': '2026-05-04',
        'posting_date': '2026-05-05',
        'amount': '-45.90',
        'currency': 'USD',
        'type': 'debit',
        'description': 'Netflix',
        'counterparty': 'Netflix',
        'category': 'other',
        'status': 'posted',
        'is_duplicate': 'false',
    },
    'c-001': {
        'transaction_id': 'c-001',
        'id_source': 'bank',
        'product_id': 'card-debit',
        'operation_date': '2026-05-03',
        'posting_date': '2026-05-04',
        'amount': '-1450.00',
        'currency': 'RUB',
        'type': 'debit',
        'description': 'Пятёрочка',
        'counterparty': 'Пятёрочка',
        'category': 'groceries',
        'status': 'posted',
        'is_duplicate': 'true',
    },
    'c-009': {
        'transaction_id': 'c-009',
        'id_source': 'bank',
        'product_id': 'card-debit',
        'operation_date': '2026-06-14',
        'posting_date': '',
        'amount': '-15000.00',
        'currency': 'RUB',
        'type': 'debit',
        'description': 'Авиабилеты',
        'counterparty': 'Аэрофлот',
        'category': 'other',
        'status': 'declined',
        'is_duplicate': 'false',
    },
}

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
        'status': 'complete',
        'extraction_source': 'server_response',
        'transactions_count': 12,
        'reason': None,
    },
    {
        'product_id': 'savings',
        'masked_number': '**** 1234',
        'status': 'complete',
        'extraction_source': 'page',
        'transactions_count': 8,
        'reason': None,
    },
    {
        'product_id': 'loan',
        'masked_number': '**** 3322',
        'status': 'complete',
        'extraction_source': 'page',
        'transactions_count': 0,
        'reason': None,
    },
]
EXPECTED_REPORT_WARNINGS = [
    'Продукт card-debit: операция c-001 совпадает с операцией',
]

# В отчёте номера и реквизиты только маскированные
FULL_NUMBERS_AND_REQUISITES = [
    '40817810500001234567',
    '40817840500007654321',
    '40817810900005551234',
    '45507810300004443322',
    '2200701234569012',
    '044525999',
    '30101810400000000999',
    'АО «Демо-банк»',
]


@pytest.mark.parametrize('statement_format', ['json', 'csv', 'both'])
def test_statement_formats_flow(
    statement_format: str, demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path
) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env | {'STORAGE__FORMAT': statement_format}, tmp_path)

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    assert run_folder.name.startswith('demo_bank_')
    assert sorted(path.name for path in run_folder.iterdir()) == EXPECTED_FILES_BY_FORMAT[statement_format]

    if statement_format in ('csv', 'both'):
        _check_csv_tables(run_folder)
    if statement_format == 'both':
        _check_csv_matches_json(run_folder)
    _check_report(run_folder)


def _check_csv_tables(run_folder: Path) -> None:
    product_columns, product_rows = _read_csv(run_folder / 'products.csv')
    assert product_columns == EXPECTED_PRODUCT_COLUMNS
    products_by_id = {row['product_id']: row for row in product_rows}
    assert list(products_by_id) == ['acc-rub', 'acc-usd', 'card-debit', 'savings', 'loan']
    for product_id, expected_row in EXPECTED_PRODUCT_ROWS.items():
        assert products_by_id[product_id] == expected_row

    transaction_columns, transaction_rows = _read_csv(run_folder / 'transactions.csv')
    assert transaction_columns == EXPECTED_TRANSACTION_COLUMNS
    assert len(transaction_rows) == NORMAL_MODE_TRANSACTIONS_COUNT
    transactions_by_id = {row['transaction_id']: row for row in transaction_rows}
    for transaction_id, expected_row in EXPECTED_TRANSACTION_ROWS.items():
        assert transactions_by_id[transaction_id] == expected_row


def _check_csv_matches_json(run_folder: Path) -> None:
    statement = json.loads((run_folder / 'statement.json').read_text(encoding='utf-8'))
    _, product_rows = _read_csv(run_folder / 'products.csv')
    _, transaction_rows = _read_csv(run_folder / 'transactions.csv')
    assert [row['product_id'] for row in product_rows] == [item['product_id'] for item in statement['products']]
    assert [row['transaction_id'] for row in transaction_rows] == [
        item['transaction_id'] for item in statement['transactions']
    ]


def _check_report(run_folder: Path) -> None:
    report_text = (run_folder / 'extraction_report.json').read_text(encoding='utf-8')
    for sensitive_value in FULL_NUMBERS_AND_REQUISITES:
        assert sensitive_value not in report_text

    report = json.loads(report_text)
    assert report['bank'] == 'demo_bank'
    assert report['period'] == {'from': DEMO_PERIOD_FROM, 'to': DEMO_PERIOD_TO}
    assert report['consent']['granted_at']
    assert 'Операции за выбранный период' in report['consent']['scope']
    assert report['products'] == EXPECTED_PRODUCT_REPORTS
    assert report['products_count'] == len(EXPECTED_PRODUCT_REPORTS)
    assert report['transactions_count'] == NORMAL_MODE_TRANSACTIONS_COUNT
    for expected_warning in EXPECTED_REPORT_WARNINGS:
        assert any(warning.startswith(expected_warning) for warning in report['warnings'])
    assert report['errors'] == []
    assert isinstance(report['duration_seconds'], float)
    assert report['duration_seconds'] > 0


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        return list(reader.fieldnames or []), rows
