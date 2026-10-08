"""Экспорт истории операций в CSV, как его выгружает кабинет демо-банка."""

import csv
import io

from .data import DemoProduct, DemoTransaction
from .formats import ValueFormat

EXPORT_COLUMNS = [
    'Дата операции',
    'Дата проведения',
    'Описание',
    'Контрагент',
    'Категория',
    'Статус',
    'Сумма',
    'Валюта',
]
# BOM — чтобы файл с кириллицей правильно открывался в Excel
EXPORT_ENCODING = 'utf-8-sig'


def build_export_csv(product: DemoProduct, transactions: list[DemoTransaction], value_format: ValueFormat) -> bytes:
    """Файл экспорта: разделитель «;», валюта кодом; даты и сумма — в формате кабинета.

    Обычный формат: '03.05.2026', '-1450,00'. Изменённый: '3 мая 2026', '-1450.00'.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';', lineterminator='\r\n')
    writer.writerow(EXPORT_COLUMNS)
    for transaction in transactions:
        posting_date = value_format.date(transaction.posting_date) if transaction.posting_date else ''
        writer.writerow(
            [
                value_format.date(transaction.operation_date),
                posting_date,
                transaction.description,
                transaction.counterparty or '',
                transaction.category,
                value_format.status(transaction),
                value_format.export_amount(transaction.amount),
                product.currency,
            ]
        )
    return buffer.getvalue().encode(EXPORT_ENCODING)
