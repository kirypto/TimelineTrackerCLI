from math import floor
from typing import Tuple


class TimeHelper:
    DAYS_PER_YEAR = 313.0
    HOURS_PER_DAY = 28.0
    MINUTES_PER_HOUR = 60.0

    @staticmethod
    def convert_time_to_ymdhm(raw: float) -> Tuple[float, float, float, float, float]:
        year_portion = raw // TimeHelper.DAYS_PER_YEAR
        raw -= year_portion * TimeHelper.DAYS_PER_YEAR
        month_portion = 0  # TODO implement month translation
        day_portion = floor(raw)
        raw -= day_portion
        hour_portion = floor(raw * TimeHelper.HOURS_PER_DAY)
        raw -= hour_portion / TimeHelper.HOURS_PER_DAY
        minute_portion = round(raw * TimeHelper.HOURS_PER_DAY * TimeHelper.MINUTES_PER_HOUR, 2)
        return year_portion, month_portion, day_portion, hour_portion, minute_portion

    @staticmethod
    def convert_time_from_ymdhm(year: float, month: float, day: float, hour: float = 0, minute: float = 0) -> float:
        if month != 0:
            # TODO implement month translation
            print("[WARN] months are not implemented and ignored for now")
        return (
                year * TimeHelper.DAYS_PER_YEAR +
                month * 0 +
                day +
                hour / TimeHelper.HOURS_PER_DAY +
                minute / TimeHelper.MINUTES_PER_HOUR / TimeHelper.HOURS_PER_DAY)

    @staticmethod
    def input_ymdh(prompt) -> float:
        print(prompt)
        year_portion = float(input("      year=") or 0)
        # month_portion = float(input("      month=") or 0)
        day_portion = float(input("      day=") or 0)
        hour_portion = float(input("      hour=") or 0)
        # if month_portion != 0:
        #     raise NotImplementedError("Month calculation not yet supported")
        return TimeHelper.convert_time_from_ymdhm(year_portion, 0, day_portion, hour_portion)