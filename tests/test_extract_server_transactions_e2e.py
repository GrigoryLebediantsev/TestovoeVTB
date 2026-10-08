import json
from pathlib import Path

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

# Операции за период: история USD — тремя порциями по «Показать ещё», карты — тремя порциями при прокрутке
EXPECTED_USD_IDS = [f'u-{number:03d}' for number in range(1, 13)]
EXPECTED_CARD_IDS = [f'c-{number:03d}' for number in range(1, 13)]
EXPECTED_PORTION_OFFSETS = [0, 5, 10]

EXPECTED_USD_SUBSCRIPTION = {
    'transaction_id': 'u-002',
    'id_source': 'bank',
    'product_id': 'acc-usd',
    'operation_date': '2026-05-04',
    'posting_date': '2026-05-05',
    'amount': -45.9,
    'currency': 'USD',
    'type': 'debit',
    'description': 'Netflix',
    'counterparty': 'Netflix',
    'category': 'other',
    'status': 'posted',
    'is_duplicate': False,
}
EXPECTED_DECLINED_CARD_PAYMENT = {
    'transaction_id': 'c-009',
    'id_source': 'bank',
    'product_id': 'card-debit',
    'operation_date': '2026-06-14',
    'posting_date': None,
    'amount': -15000.0,
    'currency': 'RUB',
    'type': 'debit',
    'description': 'Авиабилеты',
    'counterparty': 'Аэрофлот',
    'category': 'other',
    'status': 'declined',
    'is_duplicate': False,
}
EXACT_AMOUNT_TEXTS = ['"amount": -45.90', '"amount": -15000.00']

# Покупки по карте, видимые и на текущем счёте; вторая поездка в метро 25.05 на счёте не видна
EXPECTED_DUPLICATE_CARD_IDS = ['c-001', 'c-003', 'c-005', 'c-007']

LINKED_ACCOUNT_ID = 'acc-rub'

EXPECTED_SOURCES = {
    'acc-rub': ('export', 9),
    'acc-usd': ('server_response', 12),
    'card-debit': ('server_response', 12),
    'savings': ('page', 7),
    'loan': ('page', 0),
}


def test_extract_server_transactions_flow(
    demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path
) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(env, tmp_path)

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
    result = finish_program(process)

    assert result.returncode == EXIT_WITH_WARNINGS, result.output
    [run_folder] = list(output_dir.iterdir())
    statement_text = (run_folder / 'statement.json').read_text(encoding='utf-8')
    for amount_text in EXACT_AMOUNT_TEXTS:
        assert amount_text in statement_text
    statement = json.loads(statement_text)
    transactions = statement['transactions']
    transactions_by_id = {item['transaction_id']: item for item in transactions}

    # Каждая операция принадлежит ровно одному продукту из выписки
    product_ids = {product['product_id'] for product in statement['products']}
    assert len(transactions_by_id) == len(transactions)
    assert all(item['product_id'] in product_ids for item in transactions)

    # Полнота истории: все порции собраны
    assert _ids_of(transactions, 'acc-usd') == EXPECTED_USD_IDS
    assert _ids_of(transactions, 'card-debit') == EXPECTED_CARD_IDS
    assert transactions_by_id['u-002'] == EXPECTED_USD_SUBSCRIPTION
    assert transactions_by_id['c-009'] == EXPECTED_DECLINED_CARD_PAYMENT

    # Прототип не делает своих запросов: за период только порции, запрошенные самой страницей
    api_calls = demo_bank.get_api_calls()
    for product_id in ('acc-usd', 'card-debit'):
        product_calls = [call for call in api_calls if call['product_id'] == product_id]
        period_calls = [
            call for call in product_calls if call['from'] == DEMO_PERIOD_FROM and call['to'] == DEMO_PERIOD_TO
        ]
        other_calls = [call for call in product_calls if call not in period_calls]
        assert [call['offset'] for call in period_calls] == EXPECTED_PORTION_OFFSETS
        # До выставления фильтра страница успевает запросить только первую порцию без периода
        assert all(call['offset'] == 0 and call['from'] == '' for call in other_calls)
    assert {call['product_id'] for call in api_calls} == {'acc-usd', 'card-debit'}

    # Дубликаты: помечена только копия на карте
    duplicate_ids = [item['transaction_id'] for item in transactions if item['is_duplicate']]
    assert duplicate_ids == EXPECTED_DUPLICATE_CARD_IDS

    report = json.loads((run_folder / 'extraction_report.json').read_text(encoding='utf-8'))
    sources = {
        item['product_id']: (item['extraction_source'], item['transactions_count']) for item in report['products']
    }
    assert sources == EXPECTED_SOURCES
    assert report['transactions_count'] == len(transactions) == NORMAL_MODE_TRANSACTIONS_COUNT

    for card_id in EXPECTED_DUPLICATE_CARD_IDS:
        account_copy = _account_copy_of(transactions_by_id[card_id], transactions)
        expected_warning = (
            f'Продукт card-debit: операция {card_id} совпадает с операцией {account_copy["transaction_id"]} '
            f'продукта {LINKED_ACCOUNT_ID}'
        )
        assert expected_warning in report['warnings']


def _ids_of(transactions: list[dict[str, object]], product_id: str) -> list[object]:
    return [item['transaction_id'] for item in transactions if item['product_id'] == product_id]


def _account_copy_of(card_transaction: dict[str, object], transactions: list[dict[str, object]]) -> dict[str, object]:
    [account_copy] = [
        item
        for item in transactions
        if item['product_id'] == LINKED_ACCOUNT_ID
        and item['operation_date'] == card_transaction['operation_date']
        and item['amount'] == card_transaction['amount']
    ]
    return account_copy
