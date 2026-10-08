"""CSV-таблица с единообразной записью значений: стандартный csv пишет Decimal, enum и None по-разному."""

import csv
import datetime
import enum
import io
from decimal import Decimal


def dump_csv(columns: list[str], rows: list[dict[str, object]]) -> str:
    """Таблица с заголовком; заголовок пишется и для пустой таблицы."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _format_value(row[column]) for column in columns})
    return buffer.getvalue()


def _format_value(value: object) -> str:
    """None → пустая ячейка, Decimal('125430.50') → '125430.50', True → 'true', даты — ISO."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, enum.Enum):
        return _format_value(value.value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, int | float | str):
        return str(value)
    raise TypeError(f'Type is not CSV serializable: {type(value).__name__}')
