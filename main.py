from json import dumps
from typing import List, Dict, NoReturn, Optional

from timeline_tracker_gateway import TimelineTrackerGateway


class ToolThing:
    _gateway: TimelineTrackerGateway
    _current_id: Optional[str]

    def __init__(self, gateway: TimelineTrackerGateway) -> None:
        self._gateway = gateway
        self._current_id = None

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

    def doitz(self) -> NoReturn:
        while True:
            print("------------------------------")
            print(f"- Current Id: {self._current_id}")
            print("Available:")
            print("1. Get Location")
            print("2. Create Location")
            command = int(input("Input command: "))
            if command == 1:
                location_id = input("Input location id (press enter to use current id): ").strip()
                location = self._gateway.get_location(location_id if location_id else self._current_id)
                print(dumps(location, indent=2))
                self._current_id = location["id"]
            elif command == 2:
                print("Creating location...")
                location_json = {
                    "name": input("- Name: "),
                    "description": input("- Description: "),
                    "span": {
                        "latitude": {
                            "low": float(input("- Span:\n  - Latitude:\n    - Low: ")),
                            "high": float(input("    - High: ")),
                        },
                        "longitude": {
                            "low": float(input("  - Longitude:\n    - Low: ")),
                            "high": float(input("    - High: ")),
                        },
                        "altitude": {
                            "low": float(input("  - Altitude:\n    - Low: ")),
                            "high": float(input("    - High: ")),
                        },
                        "continuum": {
                            "low": float(input("  - Continuum:\n    - Low: ")),
                            "high": float(input("    - High: ")),
                        },
                        "reality": {
                            "low": float(input("  - Reality:\n    - Low: ")),
                            "high": float(input("    - High: ")),
                        },
                    },
                    "tags": self._input_tags(),
                    "metadata": self._input_metadata()
                }
                try:
                    location = self._gateway.post_location(location_json)
                    print(dumps(location, indent=2))
                    self._current_id = location["id"]
                except BaseException as e:
                    print(e)
            else:
                print(f"ERROR: Unknown command '{command}'")


def _main():
    url = "http://172.16.1.101:1337"
    gateway = TimelineTrackerGateway(url)

    tool = ToolThing(gateway)
    tool.doitz()


if __name__ == '__main__':
    _main()
