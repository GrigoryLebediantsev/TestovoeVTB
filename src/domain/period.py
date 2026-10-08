import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Period:
    date_from: datetime.date
    date_to: datetime.date

    def contains(self, date: datetime.date) -> bool:
        return self.date_from <= date <= self.date_to
