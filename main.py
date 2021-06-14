import sys
from enum import Enum
from json import dumps, loads
from math import floor
from pathlib import Path
from shutil import get_terminal_size
from typing import List, Dict, NoReturn, Optional, Any, Tuple, Type, TypeVar

from timeline_tracker_gateway import TimelineTrackerGateway

T = TypeVar("T")


class _Command(Enum):
    EXIT = 0
    FIND_ENTITY = 1
    GET_ENTITY_DETAIL = 2
    CREATE_ENTITY = 3
    MODIFY_ENTITY = 4
    GET_TIMELINE = 5
    SET_CURRENT_ID = 10
    CHANGE_UNIT_SCALE = 11
    TRANSLATE_TIME = 12
    CALCULATE_AGE = 13

    @property
    def display_text(self) -> str:
        return self.name.replace("_", " ").title()


class _EntityType(Enum):
    LOCATION = "location"
    TRAVELER = "traveler"
    EVENT = "event"


class _PatchOp(Enum):
    ADD = 1
    COPY = 5
    MOVE = 4
    REMOVE = 2
    REPLACE = 3
    TEST = 6

    @property
    def display_text(self) -> str:
        return self.name.replace("_", " ").lower()


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


class ToolThing:
    _gateway: TimelineTrackerGateway
    _current_id: Optional[str]
    _unit_scale: float

    @property
    def current_id(self) -> str:
        if self._current_id is None:
            raise ValueError("No id is set")
        return self._current_id

    @property
    def current_entity_type(self) -> _EntityType:
        return _EntityType(self.current_id.split("-")[0])

    def __init__(self, gateway: TimelineTrackerGateway, unit_scale: float) -> None:
        self._gateway = gateway
        self._current_id = None
        self._unit_scale = unit_scale

    def main_loop(self) -> NoReturn:
        while True:
            try:
                self._print_header()
                command = _Command(int(input("Input command: ")))
                if command == _Command.EXIT:
                    exit()
                elif command == _Command.CHANGE_UNIT_SCALE:
                    self._unit_scale = float(input("Input new unit scale: "))
                elif command == _Command.SET_CURRENT_ID:
                    self._current_id = input("Input an id: ")
                elif command == _Command.GET_ENTITY_DETAIL:
                    self._handle_get_entity_detail()
                elif command == _Command.CREATE_ENTITY:
                    self._handle_create_entity(self._input_entity_type())
                elif command == _Command.FIND_ENTITY:
                    self._handle_find_entity(self._input_entity_type())
                elif command == _Command.MODIFY_ENTITY:
                    self._handle_modify_entity()
                elif command == _Command.TRANSLATE_TIME:
                    time = float(input("Input Raw Time: "))
                    year, month, day, hour, minute = TimeHelper.convert_time_to_ymdhm(time)
                    print(f"{year}y, {month}m, {day}d, {hour}h, {minute}m")
                elif command == _Command.CALCULATE_AGE:
                    self._handle_calculate_age()
                elif command == _Command.GET_TIMELINE:
                    self._handle_get_timeline()
                else:
                    print(f"ERROR: Unhandled command '{command}'")
            except Exception as e:
                print(f"ERROR: {e}")

    @staticmethod
    def _input_list(name: str, item_type: Type[T], *, indent: int = 0, enforce_non_empty: bool = False) -> List[T]:
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

    @staticmethod
    def _input_metadata() -> Dict[str, str]:
        print("- Metadata (leave blank and press enter to finish):")
        metadata = {}
        while True:
            key = input("  - Key: ").strip()
            if not key:
                break
            val = input("  - Value: ").strip()
            metadata[key] = val
        return metadata

    def _input_spacial_position(self, prompt: str, *, mm_conversion: bool = False) -> float:
        print(prompt)
        km_portion = float(input("      km=") or 0)
        mm_portion = float(input("      mm=") or 0) if mm_conversion else 0
        return km_portion + self._unit_scale * mm_portion

    def _handle_get_entity_detail(self) -> None:
        entity = self._gateway.get_entity(self.current_entity_type.value, self.current_id)
        print(dumps(entity, indent=2))
        self._current_id = entity["id"]

    def _handle_create_entity(self, entity_type: _EntityType) -> None:
        print(f"Creating {entity_type.value}...")
        name = input("- Name: ")
        if not name:
            print("Empty name, aborting.")
            return
        entity_json: Dict[str, Any] = {
            "name": name,
            "description": input_multi_line("- Description: ")
        }
        if entity_type in {_EntityType.LOCATION, _EntityType.EVENT}:
            entity_json["span"] = {
                "latitude": {
                    "low": self._input_spacial_position("- Span:\n  - Latitude:\n    - Low: ", mm_conversion=True),
                    "high": self._input_spacial_position("    - High: ", mm_conversion=True),
                },
                "longitude": {
                    "low": self._input_spacial_position("  - Longitude:\n    - Low: ", mm_conversion=True),
                    "high": self._input_spacial_position("    - High: ", mm_conversion=True),
                },
                "altitude": {
                    "low": self._input_spacial_position("  - Altitude:\n    - Low: "),
                    "high": self._input_spacial_position("    - High: "),
                },
                "continuum": {
                    "low": TimeHelper.input_ymdh("  - Continuum:\n    - Low: "),
                    "high": TimeHelper.input_ymdh("    - High: "),
                },
                "reality": self._input_list("Realities", int, indent=2, enforce_non_empty=True),
            }
        if entity_type == _EntityType.TRAVELER:
            print("- Journey: ")
            entity_json["journey"] = []
            movement_types = {
                "1": "interpolated",
                "2": "immediate",
            }
            while True:
                movement_type_choice = input("  - Movement type (1=interpolated, 2=immediate, leave blank to continue): ")
                if not movement_type_choice:
                    break
                position = {
                    "latitude": self._input_spacial_position("  - Latitude: ", mm_conversion=True),
                    "longitude": self._input_spacial_position("  - Longitude: ", mm_conversion=True),
                    "altitude": self._input_spacial_position(" - Altitude: "),
                    "continuum": TimeHelper.input_ymdh(" - Continuum: "),
                    "reality": float(input(" - Reality: ") or 0),
                }
                entity_json["journey"].append({
                    "movement_type": movement_types[movement_type_choice],
                    "position": position,
                })
        if entity_type == _EntityType.EVENT:
            entity_json["affected_locations"] = self._input_list("Affected Locations", str)
            entity_json["affected_travelers"] = self._input_list("Affected Travelers", str)

        entity_json["tags"] = self._input_list("Tags", str)
        entity_json["metadata"] = self._input_metadata()

        entity = self._gateway.post_entity(entity_type.value, entity_json)
        print(dumps(entity, indent=2))
        self._current_id = entity["id"]

    def _handle_find_entity(self, entity_type: _EntityType) -> None:
        print("Enter query params:")
        filters = {
            "nameHas": input("- Name has: ") or None,
        }
        if input("Enter additional filters? ") == "y":
            filters.update({
                "taggedAll": input("- Tagged all: ") or None,
                "taggedAny": input("- Tagged any: ") or None,
                "taggedOnly": input("- Tagged only: ") or None,
                "taggedNone": input("- Tagged none: ") or None,
            })
        filters = {filterName: filterValue for filterName, filterValue in filters.items() if filterValue is not None}
        entity_name_and_ids = [
            (self._gateway.get_entity(entity_type.value, entity_id)["name"], entity_id)
            for entity_id in (self._gateway.get_entities(entity_type.value, **filters))
        ]

        if not entity_name_and_ids:
            print(f"No matching {entity_type.value}s found")
            return
        elif len(entity_name_and_ids) == 1:
            entity = entity_name_and_ids[0]
            print(f"Only one matching {entity_type.value} found, auto selecting: {entity[0]} ({entity[1]})")
            self._current_id = entity[1]
            return

        print(f"Select from the following {entity_type.value}s (the id will be stored)")
        for index, (entity_name, entity_id) in enumerate(entity_name_and_ids):
            print(f"{index}. {entity_name} ({entity_id})")
        choice = int(input("Select number: "))
        self._current_id = entity_name_and_ids[choice][1]

    def _handle_modify_entity(self) -> None:
        entity_id = self.current_id
        entity_type = self.current_entity_type
        patches = []
        patch_operation_choices = ", ".join([f"{op.display_text}={op.value}" for op in sorted(_PatchOp, key=lambda e: e.value)])
        while True:
            op_raw = input(f"Input patch 'op' ({patch_operation_choices}, or leave blank to continue): ")
            if op_raw == "":
                break
            patch_op: _PatchOp = _PatchOp(int(op_raw))
            patch = {
                "op": patch_op.name.lower(),
                "path": input("Input patch 'path': "),
            }
            if patch_op in [_PatchOp.ADD, _PatchOp.REPLACE, _PatchOp.TEST]:
                patch["value"] = input_multi_line("Input patch 'value': ")
            if patch_op in [_PatchOp.MOVE, _PatchOp.COPY]:
                patch["from"] = input("Input patch 'from': ")
            patches.append(patch)
        if not patches:
            print("Nothing to do.")
            return

        modified_entity = self._gateway.patch_entity(entity_type.value, entity_id, patches)
        print(dumps(modified_entity, indent=2))

    def _print_header(self) -> None:
        width, _ = get_terminal_size((100, 1))
        print("".join("_" for _ in range(0, width)))
        print(f"  Current Id: {self._current_id}".ljust(width - 30) + f"Unit scale: 1mm = {self._unit_scale}km  ".rjust(30))
        print("Available Commands:")
        print(f"{_Command.EXIT.value}.  {_Command.EXIT.display_text}")
        commands_sorted = sorted(filter(lambda c: c != _Command.EXIT, _Command), key=lambda c: c.value)

        col_width = 24
        num_cols = width // col_width
        index = 0
        message = ""
        for _ in range(len(commands_sorted) // num_cols + 1):
            for i in range(num_cols - 1):
                if index >= len(commands_sorted):
                    break
                command = commands_sorted[index]
                index += 1
                message += f"{command.value}. ".ljust(4)
                message += f"{command.display_text}".ljust(col_width)
            message += "\n"
        print(message)

    def _handle_calculate_age(self) -> None:
        if self._current_id is None or self.current_entity_type is not _EntityType.TRAVELER:
            print("[ERROR] A traveler id must be stored currently, aborting.")
            return
        traveler = self._gateway.get_entity(_EntityType.TRAVELER.value, self._current_id)
        age = 0
        last_timestamp = None
        for positional_move in traveler["journey"]:
            curr_timestamp = positional_move["position"]["continuum"]
            if positional_move["movement_type"] == "immediate" or last_timestamp is None:
                last_timestamp = curr_timestamp
                continue
            delta = curr_timestamp - last_timestamp
            last_timestamp = curr_timestamp
            age += delta
        years, months, days, hours, minutes = TimeHelper.convert_time_to_ymdhm(age)
        name: str = traveler['name']
        print(f"{name}'{'s' if not name.endswith('s') else ''} age is "
              f"{years} years, {months} months, {days} days, {hours} hours, and {minutes} minutes.")

    def _handle_get_timeline(self) -> None:
        valid_types = {_EntityType.LOCATION, _EntityType.TRAVELER}
        if self.current_entity_type not in valid_types:
            raise ValueError(f"Can only get timeline for: {', '.join([t.value for t in valid_types])}")
        timeline = self._gateway.get_timeline(self.current_entity_type.value, self.current_id)
        if not timeline:
            print("  <Timeline is empty>")
        for timeline_item in timeline:
            if type(timeline_item) is dict:
                print(f"- Traveled ({timeline_item['movement_type']}) to {timeline_item['position']}")
            else:
                raise NotImplementedError("Printing associated events is not yet handled")

    @staticmethod
    def _input_entity_type() -> _EntityType:
        choices = {choice_num + 1: entity_type for choice_num, entity_type in enumerate(_EntityType)}
        print("Select from the following entity types:")
        for choice_num, entity_type in choices.items():
            print(f" - {choice_num} -> {entity_type.value}")
        return choices[int(input(f"Enter entity type: "))]


def input_multi_line(prompt: str) -> str:
    result = input(prompt)
    while result.endswith("\\"):
        result = result[:-1] + "\n" + input("↪ ")
    return result


def _main(*, url: str) -> NoReturn:
    gateway = TimelineTrackerGateway(url)

    tool = ToolThing(gateway, 15.79)
    tool.main_loop()
    exit()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise ValueError("No configuration file provided")
    config = loads(Path(sys.argv[1]).read_text())
    _main(**config)
