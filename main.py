import sys
from enum import Enum
from json import dumps, loads
from pathlib import Path
from shutil import get_terminal_size
from typing import Dict, NoReturn, Optional, Any, Set, List, Union, Tuple, Iterable

from PIL.Image import Image

from map import MapView, CityMarker, BuildingMarker, MapItem, PathMarker, EventMarker
from timeline_tracker_gateway import TimelineTrackerGateway
from util import TimeHelper, input_multi_line, EntityType, input_entity_type, input_list, input_dict, get_entity_type, Span, get_image, Range, \
    input_enum, Journey, Position


class _Command(Enum):
    EXIT = 0
    FIND_ENTITY = 1
    GET_ENTITY_DETAIL = 2
    CREATE_ENTITY = 3
    MODIFY_ENTITY = 4
    TRANSLATE_ENTITY = 5
    GET_TIMELINE = 6
    APPEND_JOURNEY = 7
    SET_CURRENT_ID = 10
    CHANGE_UNIT_SCALE = 11
    CONVERT_TIME = 12
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


class _Selection:
    _unit_scale: Optional[float]
    _reality: int
    _continuum: Range
    _current_ids: List[str]
    _show_linked_events: bool

    @property
    def unit_scale(self) -> Optional[float]:
        return self._unit_scale

    @unit_scale.setter
    def unit_scale(self, value: float) -> None:
        self._unit_scale = value
        self._update_cached_selection()

    @property
    def reality(self) -> int:
        return self._reality

    @reality.setter
    def reality(self, value: int) -> None:
        self._reality = value
        self._update_cached_selection()

    @property
    def continuum(self) -> Range:
        return self._continuum

    @continuum.setter
    def continuum(self, value: Range) -> None:
        self._continuum = value
        self._update_cached_selection()

    @property
    def focus_id(self) -> str:
        if not self._current_ids:
            raise ValueError("No ids are set")
        return self._current_ids[0]

    @property
    def focus_entity_type(self) -> EntityType:
        return get_entity_type(self.focus_id)

    @property
    def current_ids(self) -> Set[str]:
        return set(self._current_ids)

    @current_ids.setter
    def current_ids(self, value: Union[Tuple[str, Iterable[str]], Iterable[str]]) -> None:
        if not value:
            self._current_ids = []
            return

        if type(value) is tuple:
            value: Tuple[str, Iterable[str]]
            focus_id, other_ids = value
        else:
            focus_id, *other_ids = value
            other_ids = set(other_ids).difference([focus_id])
        self._current_ids = [focus_id, *other_ids]
        self._update_cached_selection()

    @property
    def show_linked_events(self) -> bool:
        return self._show_linked_events

    @show_linked_events.setter
    def show_linked_events(self, value: bool) -> None:
        self._show_linked_events = value
        self._update_cached_selection()

    def __init__(
            self, *, unit_scale: float = None, current_ids: List[str] = None, continuum: Range = None, reality: int = None,
            show_linked_events: bool = None,
    ) -> None:
        cached_selection = self._load_cached_selection()
        self._unit_scale = unit_scale or cached_selection.get("unit_scale", None) or None
        self._continuum = continuum or Range(*cached_selection["continuum"].values()) if "continuum" in cached_selection else Range(0)
        self._reality = reality if reality is not None else cached_selection.get("reality", 0)
        self._current_ids = current_ids or cached_selection.get("current_ids", None) or []
        self._show_linked_events = show_linked_events or cached_selection.get("show_linked_events", None) or True

    def _update_cached_selection(self) -> None:
        selection = {
            "unit_scale": self._unit_scale,
            "continuum": {
                "low": self._continuum.low,
                "high": self._continuum.high,
            },
            "reality": self._reality,
            "current_ids": self._current_ids,
            "show_linked_events": self._show_linked_events,
        }
        selection_cache_file = self._get_cache_file()
        selection_cache_file.write_text(dumps(selection, indent=2), encoding="utf8")

    def _load_cached_selection(self) -> Dict[str, Any]:
        selection_cache_file = self._get_cache_file()
        return loads(selection_cache_file.read_text(encoding="utf8")) if selection_cache_file.exists() else {}

    @staticmethod
    def _get_cache_file() -> Path:
        return Path(__file__).parent.joinpath("__local_cache__/__selection_cache__")


class TimelineTrackerCLI:
    _gateway: TimelineTrackerGateway
    _selection: _Selection

    @property
    def unit_scale(self) -> Optional[float]:
        return self._selection.unit_scale

    @unit_scale.setter
    def unit_scale(self, scale: float) -> None:
        self._selection.unit_scale = scale

    @property
    def reality(self) -> int:
        return self._selection.reality

    @reality.setter
    def reality(self, value: int) -> None:
        self._selection.reality = value

    @property
    def continuum(self) -> Range:
        return self._selection.continuum

    @continuum.setter
    def continuum(self, value: Range) -> None:
        self._selection.continuum = value

    @property
    def focus_id(self) -> str:
        return self._selection.focus_id

    @property
    def focus_entity_type(self) -> EntityType:
        return self._selection.focus_entity_type

    @property
    def current_ids(self) -> Set[str]:
        return self._selection.current_ids

    @current_ids.setter
    def current_ids(self, value: Union[Tuple[str, Iterable[str]], Iterable[str]]) -> None:
        self._selection.current_ids = value

    def __init__(self, gateway: TimelineTrackerGateway, unit_scale: float) -> None:
        self._gateway = gateway
        self._selection = _Selection(unit_scale=unit_scale)

    def main_loop(self) -> NoReturn:
        while True:
            self._print_header()
            command = _Command(int(input("Input command: ")))
            try:
                if command == _Command.EXIT:
                    exit()
                elif command == _Command.CHANGE_UNIT_SCALE:
                    scale = input("Input new unit scale: ")
                    self.unit_scale = float(scale) if scale else None
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
                elif command == _Command.TRANSLATE_ENTITY:
                    self._handle_translate_entity()
                elif command == _Command.CONVERT_TIME:
                    time = float(input("Input Raw Time: "))
                    year, month, day, hour, minute = TimeHelper.convert_time_to_ymdhm(time)
                    print(f"{year}y, {month}m, {day}d, {hour}h, {minute}m")
                elif command == _Command.CALCULATE_AGE:
                    self._handle_calculate_age()
                elif command == _Command.GET_TIMELINE:
                    self._handle_get_timeline()
                elif command == _Command.RENDER_MAP:
                    self._handle_render_map()
                elif command == _Command.APPEND_JOURNEY:
                    self._handle_append_journey()
                else:
                    print(f"ERROR: Unhandled command '{command}'")
            except Exception as e:
                print(f"ERROR: {e}")
            except KeyboardInterrupt:
                print("\n !! Keyboard interrupt, returning to command entry. (ctrl+c again will exit)")

    def _print_header(self) -> None:
        width, _ = get_terminal_size((100, 1))
        print("".join("_" for _ in range(0, width)))
        scale = f"1mm = {self.unit_scale}km" if self.unit_scale is not None else "N/A"
        focus_id_text = self.focus_id if len(self.current_ids) > 0 else "N/A"
        print(f"  Focus Id: {focus_id_text}".ljust(width - 30) + f"Unit scale: {scale}  ".rjust(30))
        if len(self.current_ids) > 1:
            print("  Other Ids:", end="")
            other_ids = list(self.current_ids - {self.focus_id})
            index = 0
            while index < len(other_ids):
                if index % (width // 50) == 0:
                    print("\n    ", end="")
                print(other_ids[index], end="    ")
                index += 1
            print()

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
        mm_conversion &= self.unit_scale is not None
        km_portion = float(input("      km=") or 0)
        mm_portion = float(input("      mm=") or 0) if mm_conversion else 0
        result = km_portion
        if mm_conversion:
            result += self.unit_scale * mm_portion
        return result

    def _handle_get_entity_detail(self) -> None:
        entity = self._gateway.get_entity(self.focus_entity_type.value, self.focus_id)
        if self.focus_entity_type == EntityType.TRAVELER and "y" != input("  Show traveler's full journey? (y/N) ").lower():
            entity["journey"] = f"<{len(entity['journey'])} positions>"
        if "span" in entity and "y" != input(f"  Show {self.focus_entity_type.value}'s raw span? (y/N)").lower():
            span = Span(entity["span"])
            entity["span"] = {
                "latitude": str(span.latitude),
                "longitude": str(span.longitude),
                "altitude": str(span.altitude),
                "continuum": str(span.continuum),
                "reality": str(span.reality),
            }
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
        class FindResultChoice(Enum):
            Add = 0
            Replace = 1
            Remove = 2

        result_operation = input_enum(FindResultChoice, "Choose to either")
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
            if result_operation == FindResultChoice.Add:
                self.current_ids = [(entity[1]), *self.current_ids]
            elif result_operation == FindResultChoice.Replace:
                self.current_ids = [(entity[1])]
            elif result_operation == FindResultChoice.Remove:
                focus_id = [self.focus_id] if self.focus_id != entity[1] else []
                other_ids = self.current_ids.difference([*focus_id, entity[1]])
                self.current_ids = [*focus_id, *other_ids]
            else:
                raise NotImplementedError(f"Unhandled result choice '{result_operation.name}'")
            return

        print(f"Pick 1 or more (comma delimited) from the following {entity_type.value}s (or 'a' for all)")
        for index, (entity_name, entity_id) in enumerate(entity_name_and_ids):
            print(f"{index}. {entity_name} ({entity_id})")
        selections = input("Select number: ").split(",")
        chosen_ids = []
        add_all = False
        for selected in selections:
            if selected == "a":
                add_all = True
                continue
            chosen_ids.append(entity_name_and_ids[int(selected)][1])
        if add_all:
            chosen_ids.extend(set(map(lambda name_and_id: name_and_id[1], entity_name_and_ids)).difference(chosen_ids))

        if result_operation == FindResultChoice.Add:
            chosen_ids.extend(self.current_ids.difference(chosen_ids))
        elif result_operation == FindResultChoice.Remove:
            chosen_ids = self.current_ids.difference(chosen_ids)
        self.current_ids = chosen_ids

    def _handle_modify_entity(self) -> None:
        entity_id = self.focus_id
        patch_all_entities = len(self.current_ids) > 1 and "a" == input("  Modify FOCUS entity or ALL entities? (F/a) ")
        patches = []
        patch_operation_choices = ", ".join([f"{op.display_text}={op.value}" for op in sorted(_PatchOp, key=lambda e: e.value)])
        while True:
            op_raw = input(f"  Input patch 'op' ({patch_operation_choices}, or leave blank to continue): ")
            if op_raw == "":
                break
            patch_op: _PatchOp = _PatchOp(int(op_raw))
            patch = {
                "op": patch_op.name.lower(),
            }
            if patch_op in [_PatchOp.MOVE, _PatchOp.COPY]:
                patch["from"] = input("  Input patch 'from': ")
            patch["path"] = input("  Input patch 'path': ")
            if patch_op in [_PatchOp.ADD, _PatchOp.REPLACE, _PatchOp.TEST]:
                patch["value"] = input_multi_line("  Input patch 'value': ")
            patches.append(patch)
        if not patches:
            print("Nothing to do.")
            return

        to_modify = self.current_ids if patch_all_entities else [entity_id]
        for entity_id in to_modify:
            print(f"  Modifying {entity_id}:")
            modified_entity = self._gateway.patch_entity(get_entity_type(entity_id).value, entity_id, patches)
            print(dumps(modified_entity, indent=2), end="\n-----\n")

    def _handle_translate_entity(self) -> None:
        entity_id = self.focus_id
        patch_all_entities = len(self.current_ids) > 1 and "a" == input("  Modify FOCUS entity or ALL entities? (F/a) ")
        latitude_delta = float(input("  Translate latitude by: (0) ") or 0)
        longitude_delta = float(input("  Translate longitude by: (0) ") or 0)
        altitude_delta = float(input("  Translate altitude by: (0) ") or 0)
        to_modify = self.current_ids if patch_all_entities else [entity_id]
        for entity_id in to_modify:
            print(f"  Modifying {entity_id}:")
            entity_type = get_entity_type(entity_id)
            if entity_type == EntityType.LOCATION:
                entity = self._gateway.get_entity(entity_type.value, entity_id)
                span = Span(entity["span"])
                patches = []
                if latitude_delta != 0:
                    patches.extend([
                        {"op": "replace", "path": "/span/latitude/low", "value": span.latitude.low + latitude_delta},
                        {"op": "replace", "path": "/span/latitude/high", "value": span.latitude.high + latitude_delta},
                    ])
                if longitude_delta != 0:
                    patches.extend([
                        {"op": "replace", "path": "/span/longitude/low", "value": span.longitude.low + longitude_delta},
                        {"op": "replace", "path": "/span/longitude/high", "value": span.longitude.high + longitude_delta},
                    ])
                if altitude_delta != 0:
                    patches.extend([
                        {"op": "replace", "path": "/span/altitude/low", "value": span.altitude.low + altitude_delta},
                        {"op": "replace", "path": "/span/altitude/high", "value": span.altitude.high + altitude_delta},
                    ])
            else:
                print("  Skipping, entity type is not supported")
                continue

            modified_entity = self._gateway.patch_entity(entity_type.value, entity_id, patches)
            print(dumps(modified_entity, indent=2), end="\n-----\n")

    def _handle_append_journey(self) -> None:
        post_all_travelers = len(self.current_ids) > 1 and "a" == input("  Modify FOCUS entity or ALL entities? (F/a) ")

        print("  Enter new position details:")
        movement_type_choice = input("  - Movement type: (1=interpolated, 2=immediate; default=1) ")
        positional_move = {
            "movement_type": ("immediate" if movement_type_choice == "2" else "interpolated"),
            "position": {
                "latitude": self._input_spacial_position("  - Latitude: ", mm_conversion=True),
                "longitude": self._input_spacial_position("  - Longitude: ", mm_conversion=True),
                "altitude": self._input_spacial_position(" - Altitude: "),
                "continuum": TimeHelper.input_ymdh(" - Continuum: "),
                "reality": float(input(" - Reality: ") or 0),
            },
        }

        to_post_to = {self.focus_id} if not post_all_travelers else self.current_ids
        for entity_id in to_post_to:
            self._gateway.post_traveler_journey(entity_id, positional_move)

    def _handle_calculate_age(self) -> None:
        if self.focus_entity_type is not EntityType.TRAVELER:
            raise ValueError("[ERROR] A traveler id must be stored currently, aborting.")
        traveler = self._gateway.get_entity(EntityType.TRAVELER.value, self.focus_id)
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
        if self.focus_entity_type not in valid_types:
            raise ValueError(f"Can only get timeline for: {', '.join([t.value for t in valid_types])}")
        timeline = self._gateway.get_timeline(self.focus_entity_type.value, self.focus_id)
        if not timeline:
            print("  <Timeline is empty>")
        for timeline_item in timeline:
            if type(timeline_item) is dict:
                print(f"- Traveled ({timeline_item['movement_type']}) to {timeline_item['position']}")
            else:
                raise NotImplementedError("Printing associated events is not yet handled")

    def _handle_render_map(self) -> None:
        map_view = MapView()
        reality = self._selection.reality
        continuum = self.continuum
        show_linked_events = self._selection.show_linked_events
        image_key = "image-ld-url"
        print(f" Render Settings: continuum={continuum}, reality={reality}, imgQuality=Low, linkedEvents={show_linked_events}")
        if "y" == input("  Modify Settings? (y/N) ").lower():
            if "h" == input("    - Image quality: low or high? (L/h) ").lower():
                image_key = "image-hd-url"
            r = input(f"    - Enter reality: ({reality}) ")
            reality = self.reality = int(r) if r != "" else reality
            if "y" == input(f"    - Modify continuum? (y/N) ").lower():
                continuum_low = TimeHelper.input_ymdh(f"    - Enter continuum low: ")
                continuum_high = TimeHelper.input_ymdh(f"    - Enter continuum high: ")
                continuum = self.continuum = Range(continuum_low, continuum_high)
            show_linked_events = self._selection.show_linked_events = ("y" == input("    - Show linked events? (Y/n) ").lower())

        entity_ids = set(self.current_ids)
        if show_linked_events:
            for entity_id in list(entity_ids):
                entity_type = get_entity_type(entity_id)
                if entity_type not in {EntityType.LOCATION, EntityType.TRAVELER}:
                    continue
                timeline = self._gateway.get_timeline(entity_type.value, entity_id)
                for item in timeline:
                    if isinstance(item, str):
                        entity_ids.add(item)

        entities = list(map(lambda e_id: self._gateway.get_entity(get_entity_type(e_id).value, e_id), entity_ids))
        map_items = self._construct_map_representations(entities, image_key, continuum, reality)
        for map_item in map_items:
            map_view.add_item(map_item)
        map_view.render(elevation=30, azimuth=-130)

    @staticmethod
    def _construct_map_representations(entities: List[Dict[str, Any]], image_key: str, continuum: Range, reality: int) -> List[MapItem]:
        map_items: List[MapItem] = []
        for entity in entities:
            entity_id: str = entity["id"]
            entity_type = get_entity_type(entity_id)
            name = entity["name"]
            image = TimelineTrackerCLI._get_image_optional(entity, image_key)
            if entity_type == EntityType.LOCATION:
                span = Span(entity["span"])
                if not TimelineTrackerCLI._is_span_in_query_area(span, continuum, reality, print_skip=True, identifier=entity["name"]):
                    continue
                if {"city", "town", "capital"}.intersection(entity["tags"]):
                    marker_class = CityMarker
                else:
                    marker_class = BuildingMarker
                map_item = marker_class(span, image=image, label=name)
            elif entity_type == EntityType.EVENT:
                span = Span(entity["span"])
                if not TimelineTrackerCLI._is_span_in_query_area(span, continuum, reality, print_skip=True, identifier=entity["name"]):
                    continue
                map_item = EventMarker(span, image=image, label=name)
            elif entity_type == EntityType.TRAVELER:
                journey = Journey(entity["journey"])
                filtered_movements: List[Tuple[Position, bool]] = []
                was_last_included = False
                for position, is_interpolated in journey.movements:
                    if position.reality == reality and continuum.low <= position.continuum <= continuum.high:
                        filtered_movements.append((position, is_interpolated and was_last_included))
                        was_last_included = True
                    else:
                        was_last_included = False
                map_item = PathMarker(Journey(filtered_movements))
            else:
                print(f"  !! Skipping rendering {entity_id} ({entity['name']}) as type {entity_type} is not supported")
                continue
            map_items.append(map_item)
        return map_items

    @staticmethod
    def _is_span_in_query_area(span, continuum, reality, *, print_skip: bool = False, identifier: str = ""):
        is_in_query_area = True
        if reality not in span.reality:
            if print_skip:
                print(f"  !! Skipping rendering {identifier} as it is not in query reality {reality}")
            is_in_query_area = False
        if span.continuum.low > continuum.high or span.continuum.high < continuum.low:
            if print_skip:
                print(f"  !! Skipping rendering {identifier} as it is not in query continuum {continuum}")
            is_in_query_area = False
        return is_in_query_area

    @staticmethod
    def _get_image_optional(entity: Dict[str, Any], image_key: str) -> Optional[Image]:
        if image_key in entity["metadata"]:
            try:
                image = get_image(entity["metadata"][image_key])
            except RuntimeError:
                image = None
        else:
            image = None
        return image


def _main(
        *, url: Optional[str], mm_conversion: Optional[float], auth_user: Optional[str] = None, auth_pass: Optional[str] = None
) -> NoReturn:
    for config_val, expected_type in [(url, str), (mm_conversion, float)]:
        if config_val is not None and type(config_val) is not expected_type:
            raise ValueError(f"Invalid configuration, needed {expected_type}, was given {config_val}")
    auth = (auth_user, auth_pass) if auth_user and auth_pass else None
    gateway = TimelineTrackerGateway(url, auth=auth)

    tool = TimelineTrackerCLI(gateway, mm_conversion)
    tool.main_loop()
    exit()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise ValueError("No configuration file provided")
    config = loads(Path(sys.argv[1]).read_text())
    _main(**config)
