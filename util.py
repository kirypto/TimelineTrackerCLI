from enum import Enum
from json import loads
from math import floor
from typing import Tuple, Union, Type, List, TypeVar, Dict, Set, Any, Optional

T = TypeVar("T")
TK = TypeVar("TK")
TV = TypeVar("TV")


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


def _infill(length: int) -> str:
    return "".ljust(length)


def input_list(name: str, item_type: Type[T], *, indent: int = 0, enforce_non_empty: bool = False) -> List[T]:
    print(f"{_infill(indent)}- {name} (leave blank and press enter to finish):")
    tags = []
    while True:
        tag = input(f"{_infill(indent)}  - ").strip()
        if not tag:
            if not tags and enforce_non_empty:
                print(f"{_infill(indent)}  !! {name} list cannot be empty")
                continue
            else:
                break
        tags.append(item_type(tag))
    return tags


def input_dict(name: str, key_type: Type[TK], val_type: Type[TV], *, indent: int = 0) -> Dict[TK, TV]:
    print(f"{''.ljust(indent)}- {name} (leave blank and press enter to finish):")
    metadata = {}
    while True:
        key = input("  - Key: ").strip()
        if not key:
            break
        val = input("  - Value: ").strip()
        metadata[key_type(key)] = val_type(val)
    return metadata


def get_entity_type(entity_id: str) -> EntityType:
    return EntityType(entity_id.split("-")[0])


def avg(*values: float) -> float:
    return sum(values) / len(values)


class Range:
    _low: float
    _high: float

    @property
    def low(self) -> float:
        return self._low

    @property
    def high(self) -> float:
        return self._high

    def __init__(self, *limits: float) -> None:
        if len(limits) == 0 or len(limits) > 2:
            raise ValueError(f"{Range.__name__} constructor takes either 1 or 2 arguments")
        self._low = min(limits)
        self._high = max(limits)


class Span:
    _lat: Range
    _lon: Range
    _alt: Range
    _con: Range
    _rea: Set[float]

    @property
    def latitude(self) -> Range:
        return self._lat

    @property
    def longitude(self) -> Range:
        return self._lon

    @property
    def altitude(self) -> Range:
        return self._alt

    @property
    def continuum(self) -> Range:
        return self._con

    @property
    def reality(self) -> Set[float]:
        return self._rea

    def __init__(
            self, span: Optional[Dict[str, Any]],
            *, lat: Range = None, lon: Range = None, alt: Range = None, con: Range = None, rea: Set[float] = None
    ) -> None:
        self._lat = lat if lat is not None else Range(*span["latitude"].values())
        self._lon = lon if lon is not None else Range(*span["longitude"].values())
        self._alt = alt if alt is not None else Range(*span["altitude"].values())
        self._con = con if con is not None else Range(*span["continuum"].values())
        self._rea = rea if rea is not None else span["reality"]
