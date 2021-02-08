from json import dumps

from timeline_tracker_gateway import TimelineTrackerGateway


def _main():
    url = "http://172.16.1.101:1337"
    gateway = TimelineTrackerGateway(url)

    while True:
        print("------------------------------")
        print("Available:")
        print("1. Get Location")
        print("2. Create Location")
        command = int(input("Input command: "))
        if command == 1:
            location_id = input("Input location id: ")
            print(dumps(gateway.get_location(location_id), indent=2))
        elif command == 2:
            raise NotImplementedError("Welp... -_-")
        else:
            print(f"ERROR: Unknown command '{command}'")


if __name__ == '__main__':
    _main()
