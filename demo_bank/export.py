"""Экспорт истории операций в CSV, как его выгружает кабинет демо-банка."""

import csv
import io

from .data import DemoProduct, DemoTransaction

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
EXPORT_DATE_FORMAT = '%d.%m.%Y'


def build_export_csv(product: DemoProduct, transactions: list[DemoTransaction]) -> bytes:
    """Файл экспорта: разделитель «;», даты ДД.ММ.ГГГГ, сумма с запятой '-1450,00', валюта кодом."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';', lineterminator='\r\n')
    writer.writerow(EXPORT_COLUMNS)
    for transaction in transactions:
        posting_date = transaction.posting_date.strftime(EXPORT_DATE_FORMAT) if transaction.posting_date else ''
        writer.writerow(
            [
                transaction.operation_date.strftime(EXPORT_DATE_FORMAT),
                posting_date,
                transaction.description,
                transaction.counterparty or '',
                transaction.category,
                transaction.status,
                f'{transaction.amount:.2f}'.replace('.', ','),
                product.currency,
            ]
        )
    return buffer.getvalue().encode(EXPORT_ENCODING)
