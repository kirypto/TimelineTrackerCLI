from enum import Enum
from json import loads
from math import floor
from typing import Tuple, Union, Type, List, TypeVar

T = TypeVar("T")


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


class EntityType(Enum):
    LOCATION = "location"
    TRAVELER = "traveler"
    EVENT = "event"


def input_entity_type() -> EntityType:
    choices = {choice_num + 1: entity_type for choice_num, entity_type in enumerate(EntityType)}
    print("Select from the following entity types:")
    for choice_num, entity_type in choices.items():
        print(f" - {choice_num} -> {entity_type.value}")
    return choices[int(input(f"Enter entity type: "))]


def input_multi_line(prompt: str) -> Union[str, dict]:
    result = input(prompt)
    convert_to_json = result == "json\\"
    result = result.removeprefix("json")
    if convert_to_json:
        print("    JSON mode specified")
    while result.endswith("\\"):
        result = result[:-1] + "\n" + input("↪ ")
    if convert_to_json:
        result = loads(result)
    return result


def input_list(name: str, item_type: Type[T], *, indent: int = 0, enforce_non_empty: bool = False) -> List[T]:
    print(f"{''.ljust(indent)}- {name} (leave blank and press enter to finish):")
    tags = []
    while True:
        tag = input(f"{''.ljust(indent)}  - ").strip()
        if not tag:
            if not tags and enforce_non_empty:
                print(f"{''.ljust(indent)}  !! {name} list cannot be empty")
                continue
            else:
                break
        tags.append(item_type(tag))
    return tags
