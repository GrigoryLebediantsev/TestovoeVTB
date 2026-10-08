import json
import re
from pathlib import Path

from tests.e2e_support import ClientBrowser, DemoBankServer, finish_program, give_consent_and_log_in, start_program

PERIOD_FROM = '2026-05-01'
PERIOD_TO = '2026-06-30'

GENERATED_ID_PATTERN = re.compile(r'^[0-9a-f]{16}-\d+$')


def current_account_transaction(
    operation_date: str,
    posting_date: str,
    amount: float,
    description: str,
    counterparty: str,
    category: str,
) -> dict[str, object]:
    """Операция текущего счёта в выписке без идентификатора: экспорт его не содержит, он генерируется."""
    return {
        'id_source': 'generated',
        'product_id': 'acc-rub',
        'operation_date': operation_date,
        'posting_date': posting_date,
        'amount': amount,
        'currency': 'RUB',
        'type': 'debit' if amount < 0 else 'credit',
        'description': description,
        'counterparty': counterparty,
        'category': category,
        'status': 'posted',
        'is_duplicate': False,
    }


# В кабинете история счёта разбита на страницы по 4 операции: за период это три страницы,
# экспорт отдаёт операции всех страниц одним файлом. Покупка 20.04 отсекается фильтром периода.
EXPECTED_CURRENT_ACCOUNT_TRANSACTIONS = [
    current_account_transaction('2026-05-01', '2026-05-01', 85000.0, 'Зарплата за апрель', 'ООО «Работа»', 'salary'),
    current_account_transaction(
        '2026-05-03', '2026-05-04', -1450.0, 'Покупка по карте •• 9012: Пятёрочка', 'Пятёрочка', 'groceries'
    ),
    current_account_transaction(
        '2026-05-05', '2026-05-05', -50000.0, 'Перевод на накопительный счёт', 'Накопительный счёт •• 1234', 'transfer'
    ),
    current_account_transaction(
        '2026-05-12',
        '2026-05-13',
        -2300.0,
        'Покупка по карте •• 9012: Кофейня «Зерно»',
        'Кофейня «Зерно»',
        'restaurants',
    ),
    current_account_transaction(
        '2026-05-25', '2026-05-25', -63.0, 'Покупка по карте •• 9012: Метро', 'Метро', 'transport'
    ),
    current_account_transaction(
        '2026-05-30', '2026-06-01', -4999.0, 'Покупка по карте •• 9012: Озон', 'Озон', 'shopping'
    ),
    current_account_transaction('2026-06-01', '2026-06-01', 85000.0, 'Зарплата за май', 'ООО «Работа»', 'salary'),
    current_account_transaction(
        '2026-06-10', '2026-06-10', 20000.0, 'Перевод с накопительного счёта', 'Накопительный счёт •• 1234', 'top_up'
    ),
    current_account_transaction('2026-06-15', '2026-06-15', -12000.0, 'Оплата ЖКУ', 'ООО «УК Дом»', 'utilities'),
]

# Способ извлечения и число операций каждого продукта: экспорт → ответы сервера → разбор страницы
EXPECTED_SOURCES = {
    'acc-rub': ('export', 9),
    'acc-usd': ('server_response', 12),
    'card-debit': ('server_response', 12),
    'savings': ('page', 7),
    'loan': ('page', 0),
}


def test_extract_export_transactions_flow(
    demo_bank: DemoBankServer, client_browser: ClientBrowser, tmp_path: Path
) -> None:
    output_dir = tmp_path / 'output'
    env = demo_bank.program_env(client_browser_cdp_url=client_browser.cdp_url, output_dir=output_dir)
    process = start_program(
        env | {'EXTRACTION__PERIOD_FROM': PERIOD_FROM, 'EXTRACTION__PERIOD_TO': PERIOD_TO}, tmp_path
    )

    give_consent_and_log_in(client_browser.context, expected_consent_texts=[])
    result = finish_program(process)

    assert result.returncode == 0, result.output
    [run_folder] = list(output_dir.iterdir())
    statement = json.loads((run_folder / 'statement.json').read_text(encoding='utf-8'))

    current_account_transactions = [item for item in statement['transactions'] if item['product_id'] == 'acc-rub']
    generated_ids = [item.pop('transaction_id') for item in current_account_transactions]
    assert all(GENERATED_ID_PATTERN.match(generated_id) for generated_id in generated_ids)
    assert len(set(generated_ids)) == len(generated_ids)
    assert current_account_transactions == EXPECTED_CURRENT_ACCOUNT_TRANSACTIONS

    report = json.loads((run_folder / 'extraction_report.json').read_text(encoding='utf-8'))
    sources = {
        item['product_id']: (item['extraction_source'], item['transactions_count']) for item in report['products']
    }
    assert sources == EXPECTED_SOURCES
    # Скачанный файл экспорта не остаётся в папке результата
    assert sorted(path.name for path in run_folder.iterdir()) == ['extraction_report.json', 'statement.json']
