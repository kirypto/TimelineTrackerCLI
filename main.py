from enum import Enum
from json import dumps
from typing import List, Dict, NoReturn, Optional

from timeline_tracker_gateway import TimelineTrackerGateway


class _Command(Enum):
    GET_LOCATION = 3
    CREATE_LOCATION = 2
    CHANGE_UNIT_SCALE = 1


class ToolThing:
    _gateway: TimelineTrackerGateway
    _current_id: Optional[str]
    _unit_scale: float

    def __init__(self, gateway: TimelineTrackerGateway, unit_scale: float) -> None:
        self._gateway = gateway
        self._current_id = None
        self._unit_scale = unit_scale

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

    def doitz(self) -> NoReturn:
        while True:
            try:
                print("------------------------------")
                print(f"- Current Id: {self._current_id}")
                print(f"- Unit scale: 1mm = {self._unit_scale}km")
                print("Available:")
                for command in sorted(_Command, key=lambda c: c.value):
                    print(f"{command.value}. {command.name.replace('_', ' ').lower()}")
                command = _Command(int(input("Input command: ")))
                if command == _Command.CHANGE_UNIT_SCALE:
                    self._unit_scale = float(input("Input new unit scale: "))
                if command == _Command.GET_LOCATION:
                    location_id = input("Input location id (press enter to use current id): ").strip()
                    location = self._gateway.get_location(location_id if location_id else self._current_id)
                    print(dumps(location, indent=2))
                    self._current_id = location["id"]
                    continue
                if command == _Command.CREATE_LOCATION:
                    print("Creating location...")
                    location_json = {
                        "name": input("- Name: "),
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
                                "low": float(input("  - Reality:\n    - Low: ")),
                                "high": float(input("    - High: ")),
                            },
                        },
                        "tags": self._input_tags(),
                        "metadata": self._input_metadata()
                    }
                    location = self._gateway.post_location(location_json)
                    print(dumps(location, indent=2))
                    self._current_id = location["id"]
                    continue
                print(f"ERROR: Unknown command '{command}'")
            except BaseException as e:
                print(e)


def _main():
    url = "http://172.16.1.101:1337"
    gateway = TimelineTrackerGateway(url)

    tool = ToolThing(gateway, 15.79)
    tool.doitz()


if __name__ == '__main__':
    _main()
