import datetime
from dataclasses import dataclass

from .period import Period
from .product import Product
from .transaction import Transaction

RUN_FOLDER_TIME_FORMAT = '%Y%m%d-%H%M%S'


@dataclass
class Statement:
    bank: str
    extracted_at: datetime.datetime
    period: Period
    products: list[Product]
    transactions: list[Transaction]


def build_run_folder_name(bank: str, started_at: datetime.datetime) -> str:
    """Папка одного запуска: банк и время, чтобы запуски не перезаписывали друг друга."""
    return f'{bank}_{started_at.strftime(RUN_FOLDER_TIME_FORMAT)}'
