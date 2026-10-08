import json
import re
from pathlib import Path

from tests.e2e_support import (
    EXIT_WITH_WARNINGS,
    ClientBrowser,
    DemoBankServer,
    finish_program,
    give_consent_and_log_in,
    start_program,
)

GENERATED_ID_PATTERN = re.compile(r'^[0-9a-f]{16}-\d+$')


def savings_transaction(
    operation_date: str,
    posting_date: str | None,
    amount: float,
    description: str,
    counterparty: str | None,
    category: str,
    status: str,
    bank_id: str | None = None,
) -> dict[str, object]:
    """Операция накопительного счёта в выписке; у сгенерированных идентификатор проверяется отдельно."""
    return {
        'transaction_id': bank_id,
        'id_source': 'bank' if bank_id else 'generated',
        'product_id': 'savings',
        'operation_date': operation_date,
        'posting_date': posting_date,
        'amount': amount,
        'currency': 'RUB',
        'type': 'debit' if amount < 0 else 'credit',
        'description': description,
        'counterparty': counterparty,
        'category': category,
        'status': status,
        'is_duplicate': False,
    }


# Кабинет фильтрует по дате проведения: операция 30.04, проведённая 01.05, приходит из кабинета,
# но прототип отбрасывает её как совершённую вне периода. Операция 15.03 отсекается фильтром кабинета.
EXPECTED_SAVINGS_TRANSACTIONS = [
    savings_transaction(
        '2026-05-05',
        '2026-05-05',
        50000.0,
        'Пополнение с текущего счёта',
        'Текущий счёт •• 4567',
        'top_up',
        'posted',
        bank_id='sv-0002',
    ),
    savings_transaction('2026-05-20', '2026-05-20', 1000.0, 'Пополнение через СБП', 'Пётр С.', 'top_up', 'posted'),
    savings_transaction('2026-05-20', '2026-05-20', 1000.0, 'Пополнение через СБП', 'Пётр С.', 'top_up', 'posted'),
    savings_transaction('2026-05-31', '2026-05-31', 6890.41, 'Выплата процентов за май', None, 'interest', 'posted'),
    savings_transaction(
        '2026-06-10',
        '2026-06-10',
        -20000.0,
        'Перевод на текущий счёт',
        'Текущий счёт •• 4567',
        'withdrawal',
        'posted',
        bank_id='sv-0003',
    ),
    savings_transaction(
        '2026-06-15',
        None,
        -5000.0,
        'Перевод в другой банк',
        'ООО «Ромашка»',
        'transfer',
        'declined',
        bank_id='sv-0004',
    ),
    savings_transaction('2026-06-30', None, 7012.05, 'Выплата процентов за июнь', None, 'interest', 'pending'),
]
EXACT_AMOUNT_TEXTS = ['"amount": 50000.00', '"amount": -20000.00', '"amount": 6890.41']

EXPECTED_SAVINGS_REPORT = {
    'product_id': 'savings',
    'masked_number': '**** 1234',
    'status': 'complete',
    'extraction_source': 'page',
    'transactions_count': 7,
    'reason': None,
}
EXPECTED_LOAN_REPORT = {
    'product_id': 'loan',
    'masked_number': '**** 3322',
    'status': 'complete',
    'extraction_source': 'page',
    'transactions_count': 0,
    'reason': None,
}


def test_extract_page_transactions_flow(
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

    savings_transactions = [item for item in statement['transactions'] if item['product_id'] == 'savings']
    generated_ids = [item['transaction_id'] for item in savings_transactions if item['id_source'] == 'generated']
    for generated_id in generated_ids:
        assert GENERATED_ID_PATTERN.match(generated_id)
    assert len(set(generated_ids)) == len(generated_ids)
    assert [_without_generated_id(item) for item in savings_transactions] == EXPECTED_SAVINGS_TRANSACTIONS

    # Пустая история кредита — не ошибка
    assert [item for item in statement['transactions'] if item['product_id'] == 'loan'] == []

    report = json.loads((run_folder / 'extraction_report.json').read_text(encoding='utf-8'))
    product_reports = {item['product_id']: item for item in report['products']}
    assert product_reports['savings'] == EXPECTED_SAVINGS_REPORT
    assert product_reports['loan'] == EXPECTED_LOAN_REPORT
    assert report['transactions_count'] == len(statement['transactions'])
    assert 'Продукт savings: отброшено операций вне периода: 1' in report['warnings']


def _without_generated_id(transaction: dict[str, object]) -> dict[str, object]:
    if transaction['id_source'] == 'generated':
        return transaction | {'transaction_id': None}
    return transaction
