"""Как кабинет демо-банка выглядит в текущем режиме: формат значений и разметка таблицы операций."""

from dataclasses import dataclass, field

from .formats import ValueFormat


@dataclass(frozen=True)
class TableMarkup:
    """Классы строк и ячеек таблицы операций и кнопки «Показать ещё»."""

    row_class: str = 'transaction'
    cell_class_prefix: str = 'transaction-'
    show_more_class: str = 'show-more'


# Режим changed_layout: банк переименовал классы — прежние селекторы прототипа их не находят
CHANGED_TABLE_MARKUP = TableMarkup(row_class='operation', cell_class_prefix='operation-', show_more_class='load-more')


@dataclass(frozen=True)
class CabinetView:
    value_format: ValueFormat = field(default_factory=ValueFormat)
    table_markup: TableMarkup = field(default_factory=TableMarkup)
