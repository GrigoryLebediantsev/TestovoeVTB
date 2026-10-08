import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Period:
    date_from: datetime.date
    date_to: datetime.date

    def contains(self, date: datetime.date) -> bool:
        return self.date_from <= date <= self.date_to

    def contains_transaction_dates(self, operation_date: datetime.date, posting_date: datetime.date | None) -> bool:
        """Операция в периоде по дате проведения, как в фильтре кабинета; без неё — по дате операции."""
        return self.contains(posting_date or operation_date)
