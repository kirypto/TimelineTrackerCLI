from enum import Enum
from json import loads
from math import floor
from typing import Tuple, Union, Type, List, TypeVar, Dict, Set, Any, Optional
from click import edit

from PIL.Image import Image, open as img_open
from requests import get, RequestException

from cache import with_cache

T = TypeVar("T")
TK = TypeVar("TK")
TV = TypeVar("TV")
TE = TypeVar("TE", bound=Enum)


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
    def input_ymdh(prompt, *, indent: int = 6) -> float:
        print(prompt)
        spacing = "".ljust(indent, " ")
        year_portion = float(input(f"{spacing}year=") or 0)
        # month_portion = float(input(f"{spacing}month=") or 0)
        day_portion = float(input(f"{spacing}day=") or 0)
        hour_portion = float(input(f"{spacing}hour=") or 0)
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

    def __str__(self) -> str:
        return f"[{round(self._low, 3)},{round(self._high, 3)}]"


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


class Position:
    _data: Dict[str, float]

    @property
    def latitude(self) -> float:
        return self._data["latitude"]

    @property
    def longitude(self) -> float:
        return self._data["longitude"]

    @property
    def altitude(self) -> float:
        return self._data["altitude"]

    @property
    def continuum(self) -> float:
        return self._data["continuum"]

    @property
    def reality(self) -> float:
        return self._data["reality"]

    def __init__(self, data: Dict[str, float]) -> None:
        self._data = data


class Journey:
    _movements: List[Tuple[Position, bool]]

    @property
    def movements(self) -> List[Tuple[Position, bool]]:
        return self._movements

    def __init__(self, data: Union[List[dict], List[Tuple[Position, bool]]]) -> None:
        if isinstance(data[0], dict):
            self._movements = [
                (Position(movement["position"]), movement["movement_type"] == "interpolated")
                for movement in data
            ]
        else:
            self._movements = data


_MILLIS_PER_DAY = 1000 * 60 * 60 * 24


@with_cache("getImage", file=True, timeout_ms=_MILLIS_PER_DAY)
def get_image(url: str) -> Image:
    try:
        return img_open(get(url, stream=True).raw)
    except RequestException as e:
        print(f"  !! Failed to retrieve image from url '{url}': {e}")
        raise RuntimeError(f"Failed to retrieve image from url '{url}'")


def input_enum(enum_type: Type[TE], prompt: str = "Select from", *, indent: int = 2) -> TE:
    indent_spacing = "".ljust(indent)
    sorted_enum_type = sorted(enum_type, key=lambda e: e.value)
    choices = ";   ".join([f"{e.value}. {e.name}" for e in sorted_enum_type])
    default_choice = [e.value for e in sorted_enum_type][0]
    raw_choice = input(f"{indent_spacing}{prompt}:   {choices}: ({default_choice}) ")
    choice = enum_type(type(default_choice)(raw_choice) if raw_choice != "" else default_choice)
    return choice


def edit_string(
        initial_string: str, attribute_name: str = None,
        *, multi_line: bool = False, require_save: bool = False, **kwargs
) -> str:
    delimiter = "".ljust(25, "=") + " do not modify this line " + "".ljust(25, "=") + "\n"
    header = "".ljust(len(delimiter) - 1, "=") + "\n"
    header += f"| Enter {attribute_name.upper() if attribute_name is not None else 'text'} after the delimiter below.\n"
    if multi_line:
        header += "| Multiple lines are permitted for this attribute.\n"
    else:
        header += "| Only a single line is permitted, additional lines will be ignored.\n"
    header += delimiter
    output_string = edit(header + initial_string, require_save=require_save, **kwargs)
    try:
        index = output_string.index(delimiter)
    except ValueError as e:
        raise ValueError("Could not locate delimiter in edited text.", e)
    edited_text = output_string[index + len(delimiter):]
    if not multi_line:
        edited_text = edited_text.splitlines(keepends=False)[0]
    return edited_text
