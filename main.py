import sys
from enum import Enum
from json import dumps, loads
from pathlib import Path
from shutil import get_terminal_size
from typing import Dict, NoReturn, Optional, Any, Set

from map import MapView, RectangularCuboid
from timeline_tracker_gateway import TimelineTrackerGateway
from util import TimeHelper, input_multi_line, EntityType, input_entity_type, input_list, input_dict, get_entity_type


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
    RENDER_MAP = 14

    @property
    def display_text(self) -> str:
        return self.name.replace("_", " ").title()


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


class ToolThing:
    _gateway: TimelineTrackerGateway
    _current_ids: Set[str]
    _unit_scale: Optional[float]

    @property
    def current_id(self) -> str:
        if not self._current_ids:
            raise ValueError("No id is set")
        elif len(self._current_ids) > 1:
            raise ValueError("More than 1 id is set")
        return list(self._current_ids)[0]

    @property
    def current_ids(self) -> Set[str]:
        return self._current_ids
    
    @current_ids.setter
    def current_ids(self, value: Set[str]) -> None:
        self._current_ids = value

    @property
    def current_entity_type(self) -> EntityType:
        return get_entity_type(self.current_id)

    def __init__(self, gateway: TimelineTrackerGateway, unit_scale: float) -> None:
        self._gateway = gateway
        self._current_ids = set()
        self._unit_scale = unit_scale

    def main_loop(self) -> NoReturn:
        while True:
            self._print_header()
            command = _Command(int(input("Input command: ")))
            try:
                if command == _Command.EXIT:
                    exit()
                elif command == _Command.CHANGE_UNIT_SCALE:
                    scale = input("Input new unit scale: ")
                    self._unit_scale = float(scale) if scale else None
                elif command == _Command.SET_CURRENT_ID:
                    self.current_ids = {input("Input an id: ")}
                elif command == _Command.GET_ENTITY_DETAIL:
                    self._handle_get_entity_detail()
                elif command == _Command.CREATE_ENTITY:
                    self._handle_create_entity(input_entity_type())
                elif command == _Command.FIND_ENTITY:
                    self._handle_find_entity(input_entity_type())
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
                elif command == _Command.RENDER_MAP:
                    self._handle_render_map()
                else:
                    print(f"ERROR: Unhandled command '{command}'")
            except Exception as e:
                print(f"ERROR: {e}")
            except KeyboardInterrupt:
                print("\n !! Keyboard interrupt, returning to command entry. (ctrl+c again will exit)")

    def _print_header(self) -> None:
        width, _ = get_terminal_size((100, 1))
        print("".join("_" for _ in range(0, width)))
        scale = f"1mm = {self._unit_scale}km" if self._unit_scale is not None else "N/A"
        if len(self.current_ids) == 1:
            print(f"  Current Id: {self.current_id}".ljust(width - 30) + f"Unit scale: {scale}  ".rjust(30))
        else:
            print(f"  Current Ids: ".ljust(width - 30) + f"Unit scale: {scale}  ".rjust(30))
            for id_ in self.current_ids:
                print(f"    - {id_}")
        print("Available Commands:")
        print(f"{_Command.EXIT.value}.  {_Command.EXIT.display_text}")
        commands_sorted = sorted(filter(lambda c: c != _Command.EXIT, _Command), key=lambda c: c.value)

        col_width = 24
        num_cols = width // col_width
        index = 0
        message = ""
        while index < len(commands_sorted):
            for i in range(num_cols - 1):
                if index >= len(commands_sorted):
                    break
                command = commands_sorted[index]
                index += 1
                message += f"{command.value}. ".ljust(4)
                message += f"{command.display_text}".ljust(col_width)
            message += "\n"
        print(message)

    def _input_spacial_position(self, prompt: str, *, mm_conversion: bool = False) -> float:
        print(prompt)
        mm_conversion &= self._unit_scale is not None
        km_portion = float(input("      km=") or 0)
        mm_portion = float(input("      mm=") or 0) if mm_conversion else 0
        result = km_portion
        if mm_conversion:
            result += self._unit_scale * mm_portion
        return result

    def _handle_get_entity_detail(self) -> None:
        entity = self._gateway.get_entity(self.current_entity_type.value, self.current_id)
        print(dumps(entity, indent=2))

    def _handle_create_entity(self, entity_type: EntityType) -> None:
        print(f"Creating {entity_type.value}...")
        name = input("- Name: ")
        if not name:
            print("Empty name, aborting.")
            return
        entity_json: Dict[str, Any] = {
            "name": name,
            "description": input_multi_line("- Description: ")
        }
        if entity_type in {EntityType.LOCATION, EntityType.EVENT}:
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
                "reality": input_list("Realities", int, indent=2, enforce_non_empty=True),
            }
        if entity_type == EntityType.TRAVELER:
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
        if entity_type == EntityType.EVENT:
            entity_json["affected_locations"] = input_list("Affected Locations", str)
            entity_json["affected_travelers"] = input_list("Affected Travelers", str)

        entity_json["tags"] = input_list("Tags", str)
        entity_json["metadata"] = input_dict("Metadata", str, str)

        entity = self._gateway.post_entity(entity_type.value, entity_json)
        print(dumps(entity, indent=2))
        self.current_ids = {entity["id"]}

    def _handle_find_entity(self, entity_type: EntityType) -> None:
        print("Enter query params:")
        filters = {
            "nameHas": input("- Name has: ") or None,
        }
        if not filters["nameHas"] or input("Enter additional filters? ") == "y":
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
            print(f"   Only one matching {entity_type.value} found, auto selecting: {entity[0]} ({entity[1]})")
            self.current_ids = {entity[1]}
            return

        print(f"Pick 1 or more (comma delimited) from the following {entity_type.value}s (or 'a' for all)")
        for index, (entity_name, entity_id) in enumerate(entity_name_and_ids):
            print(f"{index}. {entity_name} ({entity_id})")
        choice_raw = input("Select number: ")
        if choice_raw == "a":
            self.current_ids = set(map(lambda name_and_id: name_and_id[1], entity_name_and_ids))
        elif "," in choice_raw:
            self.current_ids = set(map(lambda choice: entity_name_and_ids[int(choice)][1], choice_raw.split(",")))
        else:
            self.current_ids = {entity_name_and_ids[int(choice_raw)][1]}

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

    def _handle_calculate_age(self) -> None:
        if self.current_entity_type is not EntityType.TRAVELER:
            raise ValueError("[ERROR] A traveler id must be stored currently, aborting.")
        traveler = self._gateway.get_entity(EntityType.TRAVELER.value, self.current_id)
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
        valid_types = {EntityType.LOCATION, EntityType.TRAVELER}
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

    def _handle_render_map(self) -> None:
        map_view = MapView()
        for entity_id in self.current_ids:
            entity_type = get_entity_type(entity_id)
            entity = self._gateway.get_entity(entity_type.value, entity_id)
            if entity_type == EntityType.LOCATION:
                span = entity["span"]
                span_rectangle = RectangularCuboid(
                    span["latitude"]["low"], span["longitude"]["low"], span["altitude"]["low"],
                    span["latitude"]["high"], span["longitude"]["high"], span["altitude"]["high"])
                map_view.draw(span_rectangle, "green")
            else:
                raise NotImplementedError(f"Rendering entities of type {entity_type} is not yet supported")
        map_view.render()


def _main(*, url: Optional[str], mm_conversion: Optional[float]) -> NoReturn:
    for config_val, expected_type in [(url, str), (mm_conversion, float)]:
        if config_val is not None and type(config_val) is not expected_type:
            raise ValueError(f"Invalid configuration, needed {expected_type}, was given {config_val}")
    gateway = TimelineTrackerGateway(url)

    tool = ToolThing(gateway, mm_conversion)
    tool.main_loop()
    exit()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise ValueError("No configuration file provided")
    config = loads(Path(sys.argv[1]).read_text())
    _main(**config)
