import json
from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    finish_program,
    give_consent_and_log_in,
    start_program,
)

PERIOD_FROM = '2026-05-01'
PERIOD_TO = '2026-06-30'

EXPECTED_PRODUCTS = {
    'acc-rub': {
        'product_id': 'acc-rub',
        'type': 'account',
        'name': 'Текущий счёт',
        'masked_number': '**** 4567',
        'currency': 'RUB',
        'balance': 125430.5,
        'available_balance': 125430.5,
        'linked_account_id': None,
        'requisites': {
            'account_number': '40817810500001234567',
            'bic': '044525999',
            'correspondent_account': '30101810400000000999',
            'bank_name': 'АО «Демо-банк»',
        },
        'details': {'interest_rate': None, 'opened_at': '2021-03-15', 'credit_limit': None, 'debt': None},
    },
    'acc-usd': {
        'product_id': 'acc-usd',
        'type': 'account',
        'name': 'Счёт в долларах',
        'masked_number': '**** 4321',
        'currency': 'USD',
        'balance': 2350.0,
        'available_balance': 2350.0,
        'linked_account_id': None,
        'requisites': {
            'account_number': '40817840500007654321',
            'bic': '044525999',
            'correspondent_account': '30101810400000000999',
            'bank_name': 'АО «Демо-банк»',
        },
        'details': {'interest_rate': None, 'opened_at': '2022-07-01', 'credit_limit': None, 'debt': None},
    },
    'card-debit': {
        'product_id': 'card-debit',
        'type': 'card',
        'name': 'Дебетовая карта',
        'masked_number': '**** 9012',
        'currency': 'RUB',
        'balance': 125430.5,
        'available_balance': 120430.5,
        'linked_account_id': 'acc-rub',
        'requisites': None,
        'details': {'interest_rate': None, 'opened_at': '2021-03-20', 'credit_limit': None, 'debt': None},
    },
    'savings': {
        'product_id': 'savings',
        'type': 'deposit',
        'name': 'Накопительный счёт',
        'masked_number': '**** 1234',
        'currency': 'RUB',
        'balance': 500000.0,
        'available_balance': 500000.0,
        'linked_account_id': None,
        'requisites': {
            'account_number': '40817810900005551234',
            'bic': '044525999',
            'correspondent_account': '30101810400000000999',
            'bank_name': 'АО «Демо-банк»',
        },
        'details': {'interest_rate': 16.5, 'opened_at': '2024-01-10', 'credit_limit': None, 'debt': None},
    },
    'loan': {
        'product_id': 'loan',
        'type': 'loan',
        'name': 'Потребительский кредит',
        'masked_number': '**** 3322',
        'currency': 'RUB',
        'balance': None,
        'available_balance': None,
        'linked_account_id': None,
        'requisites': {
            'account_number': '45507810300004443322',
            'bic': '044525999',
            'correspondent_account': '30101810400000000999',
            'bank_name': 'АО «Демо-банк»',
        },
        'details': {'interest_rate': 21.9, 'opened_at': '2025-02-01', 'credit_limit': None, 'debt': 230000.0},
    },
}

FULL_CARD_NUMBER_VARIANTS = ['2200701234569012', '2200 7012 3456 9012']
CLIENT_FULL_NAME = 'Иванов Иван Иванович'
CONSENT_PAGE_TEXTS = ['Демо-банк', '01.05.2026 — 30.06.2026', 'Реквизиты счетов', 'Операции за выбранный период']
# Суммы в JSON — числа ровно с двумя знаками
EXACT_AMOUNT_TEXTS = ['"balance": 125430.50', '"available_balance": 120430.50', '"debt": 230000.00']


def test_extract_products_flow(demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(
        env | {'EXTRACTION__PERIOD_FROM': PERIOD_FROM, 'EXTRACTION__PERIOD_TO': PERIOD_TO}, tmp_path
    )

    give_consent_and_log_in(client_browser.context, expected_consent_texts=CONSENT_PAGE_TEXTS)
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    assert run_folder.name.startswith('demo_bank_')

    statement_text = (run_folder / 'statement.json').read_text(encoding='utf-8')
    for amount_text in EXACT_AMOUNT_TEXTS:
        assert amount_text in statement_text
    statement = json.loads(statement_text)
    assert statement['bank'] == 'demo_bank'
    assert statement['period'] == {'from': PERIOD_FROM, 'to': PERIOD_TO}
    assert statement['extracted_at'].endswith('Z') or statement['extracted_at'].endswith('+00:00')
    assert {product['product_id']: product for product in statement['products']} == EXPECTED_PRODUCTS

    report = json.loads((run_folder / 'extraction_report.json').read_text(encoding='utf-8'))
    assert report['bank'] == 'demo_bank'
    assert report['period'] == {'from': PERIOD_FROM, 'to': PERIOD_TO}
    assert report['consent']['granted_at']
    assert report['consent']['scope']
    assert report['products_count'] == 5

    all_output = result.output + ''.join(path.read_text(encoding='utf-8') for path in run_folder.iterdir())
    for card_number in FULL_CARD_NUMBER_VARIANTS:
        assert card_number not in all_output
    assert CLIENT_FULL_NAME not in all_output
