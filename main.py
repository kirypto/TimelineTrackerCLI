from enum import Enum
from json import dumps
from typing import List, Dict, NoReturn, Optional

from timeline_tracker_gateway import TimelineTrackerGateway


class _Command(Enum):
    # Location
    CREATE_LOCATION = 3
    GET_LOCATION_DETAIL = 2
    FIND_LOCATION = 1
    MODIFY_LOCATION = 4
    # Other
    CHANGE_UNIT_SCALE = 6
    SET_CURRENT_ID = 5

    @property
    def display_text(self) -> str:
        return self.name.replace("_", " ").title()


class _EntityType(Enum):
    LOCATION = "location"


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
    _current_id: Optional[str]
    _unit_scale: float

    @property
    def current_id(self) -> str:
        if self._current_id is None:
            raise ValueError("No id is set")
        return self._current_id

    def __init__(self, gateway: TimelineTrackerGateway, unit_scale: float) -> None:
        self._gateway = gateway
        self._current_id = None
        self._unit_scale = unit_scale

    def doitz(self) -> NoReturn:
        while True:
            try:
                print("------------------------------")
                print(f"- Current Id: {self._current_id}")
                print(f"- Unit scale: 1mm = {self._unit_scale}km")
                print("Available:")
                for command in sorted(_Command, key=lambda c: c.value):
                    print(f"{command.value}. {command.display_text}")
                command = _Command(int(input("Input command: ")))
                if command == _Command.CHANGE_UNIT_SCALE:
                    self._unit_scale = float(input("Input new unit scale: "))
                elif command == _Command.SET_CURRENT_ID:
                    self._current_id = input("Input an id: ")
                elif command == _Command.GET_LOCATION_DETAIL:
                    self.handle_get_location_detail()
                elif command == _Command.CREATE_LOCATION:
                    self._handle_create_location()
                elif command == _Command.FIND_LOCATION:
                    self._handle_find_entity(_EntityType.LOCATION)
                elif command == _Command.MODIFY_LOCATION:
                    self._handle_modify_entity(_EntityType.LOCATION)
                else:
                    print(f"ERROR: Unknown command '{command}'")
            except BaseException as e:
                print(f"ERROR: {e}")

    @staticmethod
    def _input_tags() -> List[str]:
        print("- Tags (leave blank and press enter to finish):")
        tags = []
        while True:
            tag = input("  - ").strip()
            if not tag:
                break
            tags.append(tag)
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

    def _input_time_position(self, prompt) -> float:
        print(prompt)
        year_portion = float(input("      year=") or 0)
        month_portion = float(input("      month=") or 0)
        day_portion = float(input("      day=") or 0)
        hour_portion = float(input("      hour=") or 0)
        if month_portion != 0:
            raise NotImplementedError("Month calculation not yet supported")
        return 313 * year_portion + day_portion + hour_portion / 28.0

    def handle_get_location_detail(self):
        location = self._gateway.get_location(self.current_id)
        print(dumps(location, indent=2))
        self._current_id = location["id"]

    def _handle_create_location(self):
        print("Creating location...")
        name = input("- Name: ")
        if not name:
            print("Empty name, aborting.")
            return
        location_json = {
            "name": name,
            "description": input("- Description: "),
            "span": {
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
                    "low": self._input_time_position("  - Continuum:\n    - Low: "),
                    "high": self._input_time_position("    - High: "),
                },
                "reality": {
                    "low": float(input("  - Reality:\n    - Low: ") or 0),
                    "high": float(input("    - High: ") or 0),
                },
            },
            "tags": self._input_tags(),
            "metadata": self._input_metadata()
        }
        location = self._gateway.post_location(location_json)
        print(dumps(location, indent=2))
        self._current_id = location["id"]

    def _handle_find_entity(self, entity_type: _EntityType) -> None:
        print("Enter query params:")
        filters = {
            "nameIs": input("- Name is: ") or None,
            "nameHas": input("- Name has: ") or None,
            "taggedAll": input("- Tagged all: ") or None,
            "taggedAny": input("- Tagged any: ") or None,
            "taggedOnly": input("- Tagged only: ") or None,
            "taggedNone": input("- Tagged none: ") or None,
        }
        filters = {filterName: filterValue for filterName, filterValue in filters.items() if filterValue is not None}
        if entity_type == _EntityType.LOCATION:
            entity_name_and_ids = [
                (self._gateway.get_location(entity_id)["name"], entity_id)
                for entity_id in (self._gateway.get_locations(**filters))
            ]
        else:
            raise NotImplementedError(f"Entity type '{entity_type.value}' is not supported")

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

    def _handle_modify_entity(self, entity_type: _EntityType) -> None:
        entity_id = self.current_id
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
                patch["value"] = input("Input patch 'value': ")
            if patch_op in [_PatchOp.MOVE, _PatchOp.COPY]:
                patch["from"] = input("Input patch 'from': ")
            patches.append(patch)
        if not patches:
            print("Nothing to do.")
            return

        if entity_type == _EntityType.LOCATION:
            modified_entity = self._gateway.patch_location(entity_id, patches)
        else:
            raise NotImplementedError(f"Entity type '{entity_type.value}' is not supported")
        print(dumps(modified_entity, indent=2))


def _main():
    url = "http://172.16.1.101:1337"
    gateway = TimelineTrackerGateway(url)

    tool = ToolThing(gateway, 15.79)
    tool.doitz()


if __name__ == '__main__':
    _main()
