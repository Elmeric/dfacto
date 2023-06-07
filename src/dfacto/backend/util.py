# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import NamedTuple, cast

# def quarter_from_month(month: int) -> int:
#     return (month - 1) // 3 + 1
#
#
# def last_quarter(date_: date) -> "Period":
#     year, month = date_.year, date_.month
#     quarter = quarter_from_month(month)
#     if quarter == 1:
#         return Period.from_quarter(year - 1, 4)
#     return Period.from_quarter(year, quarter - 1)


@dataclass
class DatetimeRange:
    from_: datetime
    to: datetime


class Period(NamedTuple):
    start: date = date(1970, 1, 1)
    end: date = date.today()

    @property
    def start_time(self) -> datetime:
        return datetime.combine(self.start, datetime.min.time())

    @property
    def end_time(self) -> datetime:
        return datetime.combine(self.end, datetime.max.time())

    @classmethod
    def from_quarter(cls, year: int, quarter: int) -> "Period":
        last_day = 31 if quarter in (1, 4) else 30
        return cls(
            date(year, 1 + (quarter - 1) * 3, 1),
            date(year, quarter * 3, last_day)
        )

    @classmethod
    def from_current_month(cls) -> "Period":
        end = date.today()
        start = end.replace(day=1)
        return cls(start, end)

    @classmethod
    def from_last_month(cls) -> "Period":
        end = date.today().replace(day=1) - timedelta(
            days=1
        )  # veille du 1er jour du mois en cours
        start = end.replace(day=1)
        return cls(start, end)

    @classmethod
    def from_current_quarter(cls) -> "Period":
        end = date.today()
        quarter = (end.month - 1) // 3 + 1
        start = date(end.year, 1 + (quarter - 1) * 3, 1)
        return cls(start, end)

    @classmethod
    def from_last_quarter(cls) -> "Period":
        today = date.today()
        quarter = (today.month - 1) // 3 + 1
        if quarter == 1:
            return cls.from_quarter(today.year - 1, 4)
        return cls.from_quarter(today.year, quarter - 1)

    @classmethod
    def from_current_year(cls) -> "Period":
        end = date.today()
        start = end.replace(day=1, month=1)
        return cls(start, end)

    @classmethod
    def from_last_year(cls) -> "Period":
        end = date.today().replace(day=1, month=1) - timedelta(
            days=1
        )  # veille du 1er jour de l'année en cours
        start = end.replace(day=1, month=1)
        return cls(start, end)

    def __contains__(self, item) -> bool:
        if isinstance(item, datetime):
            return self.start_time <= item <= self.end_time
        if isinstance(item, date):
            return self.start <= item <= self.end
        raise ValueError("Item shall be a date or datetime instance")


class PeriodFilter(enum.Enum):
    CURRENT_MONTH = enum.auto()
    CURRENT_QUARTER = enum.auto()
    CURRENT_YEAR = enum.auto()
    LAST_MONTH = enum.auto()
    LAST_QUARTER = enum.auto()
    LAST_YEAR = enum.auto()

    def as_period(self) -> Period:
        method = f"from_{self.name.lower()}"
        return cast(Period, getattr(Period, method)())


if __name__ == "__main__":
    for f in PeriodFilter:
        print(f.name, f.as_period())
    for q in range(4):
        print(Period.from_quarter(2023, q+1))
    print(date(2023, 2, 11) in Period.from_last_quarter())
    print(datetime(2023, 6, 11, 0, 0) in Period.from_current_quarter())
    print((2023, 2, 11) in Period.from_last_quarter())
