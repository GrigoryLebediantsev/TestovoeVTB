import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Period:
    date_from: datetime.date
    date_to: datetime.date
