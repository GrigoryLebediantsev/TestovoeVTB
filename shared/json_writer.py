"""JSON с точными десятичными числами: стандартный json пишет Decimal только строкой или float."""

import datetime
import enum
import json
from decimal import Decimal

INDENT = '  '


def dump_json(value: object) -> str:
    """Форматированный JSON; Decimal пишется числом как есть: Decimal('125430.50') → 125430.50."""
    return _dump_value(value, level=0)


def _dump_value(value: object, level: int) -> str:
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, enum.Enum):
        return _dump_value(value.value, level)
    if isinstance(value, datetime.date):
        return json.dumps(value.isoformat())
    if isinstance(value, dict):
        return _dump_dict(value, level)
    if isinstance(value, list | tuple):
        return _dump_list(list(value), level)
    if value is None or isinstance(value, bool | int | float | str):
        return json.dumps(value, ensure_ascii=False)
    raise TypeError(f'Type is not JSON serializable: {type(value).__name__}')


def _dump_dict(value: dict[object, object], level: int) -> str:
    if not value:
        return '{}'
    inner_indent = INDENT * (level + 1)
    lines = [
        f'{inner_indent}{json.dumps(str(key), ensure_ascii=False)}: {_dump_value(item, level + 1)}'
        for key, item in value.items()
    ]
    return '{\n' + ',\n'.join(lines) + f'\n{INDENT * level}}}'


def _dump_list(value: list[object], level: int) -> str:
    if not value:
        return '[]'
    inner_indent = INDENT * (level + 1)
    lines = [f'{inner_indent}{_dump_value(item, level + 1)}' for item in value]
    return '[\n' + ',\n'.join(lines) + f'\n{INDENT * level}]'
