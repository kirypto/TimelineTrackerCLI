from abc import ABC, abstractmethod
from math import cos, sin, radians
from random import uniform
from typing import Tuple, List, Optional, Set, Union, Iterable

from PIL.Image import Image
from matplotlib import pyplot
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure, figaspect
from mpl_toolkits.mplot3d import Axes3D

from util import avg, Span, Range, Position, Journey

LineData = Tuple[List[float], List[float], List[float]]
Colour = Tuple[float, float, float, float]
AxesLimit = Tuple[float, float]
Point3D = Tuple[float, float, float]
MapObjectData = Union[Span, Journey]


class Colours:
    Black: Colour = (0., 0., 0., 1.)
    Silver: Colour = (192 / 255, 192 / 255, 192 / 255, 1.)
    Gray: Colour = (128 / 255, 128 / 255, 128 / 255, 1.)
    White: Colour = (1., 1., 1., 1.)
    Maroon: Colour = (128 / 255, 0., 0., 1.)
    Red: Colour = (1., 0., 0., 1.)
    Purple: Colour = (128 / 255, 0., 128 / 255, 1.)
    Fuchsia: Colour = (1., 0., 1., 1.)
    Green: Colour = (0., 128 / 255, 0., 1.)
    Lime: Colour = (0., 1., 0., 1.)
    Olive: Colour = (128 / 255, 128 / 255, 0., 1.)
    Yellow: Colour = (1., 1., 0., 1.)
    Navy: Colour = (0., 0., 128 / 255, 1.)
    Blue: Colour = (0., 0., 1., 1.)
    Teal: Colour = (0., 128 / 255, 128 / 255, 1.)
    Aqua: Colour = (0., 1., 1., 1.)
    Orange: Colour = (1., 165 / 255, 0., 1.)


class MapItem(ABC):
    _object_data: MapObjectData
    _image: Image
    _colour: Colour
    _label: str

    def __init__(self, object_data: MapObjectData, *, image: Image = None, colour: Colour = Colours.Black, label: str = None) -> None:
        self._object_data = object_data
        self._image = image
        self._colour = colour
        self._label = label

    @property
    def colour(self) -> Colour:
        return self._colour

    @property
    def image(self) -> Optional[Image]:
        return self._image

    @property
    def label(self) -> str:
        return self._label

    @property
    @abstractmethod
    def line_data(self) -> List[LineData]:
        pass

    @property
    def limits(self) -> Tuple[AxesLimit, AxesLimit, AxesLimit]:
        if isinstance(self._object_data, Span):
            span = self._object_data
            return (
                (span.latitude.low, span.latitude.high),
                (span.longitude.low, span.longitude.high),
                (span.altitude.low, span.altitude.high),
            )
        else:
            journey = self._object_data
            latitude_low = latitude_high = longitude_low = longitude_high = altitude_low = altitude_high = None
            for position, is_interpolated in journey.movements:
                if latitude_low is None:
                    latitude_low = latitude_high = position.latitude
                    longitude_low = longitude_high = position.longitude
                    altitude_low = altitude_high = position.altitude
                else:
                    latitude_low = min(latitude_low, position.latitude)
                    latitude_high = max(latitude_high, position.latitude)
                    longitude_low = min(longitude_low, position.longitude)
                    longitude_high = max(longitude_high, position.longitude)
                    altitude_low = min(altitude_low, position.altitude)
                    altitude_high = max(altitude_high, position.altitude)
            return (
                (latitude_low, latitude_high),
                (longitude_low, longitude_high),
                (altitude_low, altitude_high),
            )

    @staticmethod
    def sort_for_map_view(map_items: Iterable["MapItem"]) -> List["MapItem"]:
        def sort_key(map_item: MapItem) -> Tuple[int, float]:
            if isinstance(map_item._object_data, Span):
                span: Span = map_item._object_data
                return 0, span.altitude.low
            else:
                journey: Journey = map_item._object_data
                return 1, avg(*[position.altitude for position, _ in journey.movements])

        return sorted(map_items, key=sort_key)


class CityMarker(MapItem):
    _line_data: Optional[List[LineData]]

    @property
    def line_data(self) -> List[LineData]:
        if not self._line_data:
            span: Span = self._object_data
            self._line_data = [
                _generate_octagon(span.latitude, span.longitude, span.altitude.low),
            ]
        return self._line_data

    def __init__(self, span: Span, *, colour: Colour = Colours.Green, image: Image = None, label: str = None) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        colour_mutated = _randomize_colour(colour)
        super(CityMarker, self).__init__(span, colour=colour_mutated, image=image, label=label)
        self._line_data = None


class CuboidMarker(MapItem):
    _line_data: Optional[List[LineData]]

    @property
    def line_data(self) -> List[LineData]:
        if not self._line_data:
            span: Span = self._object_data
            self._line_data = _generate_cuboid(
                span.latitude.low, span.latitude.high,
                span.longitude.low, span.longitude.high,
                span.altitude.low, span.altitude.high
            )
        return self._line_data

    def __init__(self, span: Span, *, colour: Colour = Colours.Black, image: Image = None, label: str = None) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        colour_mutated = _randomize_colour(colour)
        super(CuboidMarker, self).__init__(span, colour=colour_mutated, image=image, label=label)
        self._line_data = None


class EventMarker(CuboidMarker):
    def __init__(self, span: Span, *, colour: Colour = Colours.Orange, image: Image = None, label: str = None) -> None:
        super().__init__(span, colour=colour, image=image, label=label)


class BuildingMarker(CuboidMarker):
    def __init__(self, span: Span, *, colour: Colour = Colours.Lime, image: Image = None, label: str = None) -> None:
        super().__init__(span, colour=colour, image=image, label=label)


class PathMarker(MapItem):
    _line_data: Optional[List[LineData]]

    @property
    def line_data(self) -> List[LineData]:
        if not self._line_data:
            def to_point(_position: Position) -> Point3D:
                return _position.latitude, _position.longitude, _position.altitude

            journey: Journey = self._object_data
            all_lines: List[LineData] = []
            current_line = None
            for position, is_interpolated in journey.movements:
                if current_line is None:
                    current_line = [position]
                elif is_interpolated:
                    current_line.append(position)
                else:
                    all_lines.append(_convert_to_line_data([to_point(position) for position in current_line]))
                    current_line = []
            if current_line is not None:
                all_lines.append(_convert_to_line_data([to_point(position) for position in current_line]))
            self._line_data = all_lines
        return self._line_data

    def __init__(self, journey: Journey, *, colour: Colour = Colours.Blue, image: Image = None, label: str = None) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        colour_mutated = _randomize_colour(colour)
        super().__init__(journey, image=image, colour=colour_mutated, label=label)
        self._line_data = None


class MapView:
    _figure: Figure
    _axes_3d: Axes3D
    _axes_2d: Axes
    _map_items: Set[MapItem]

    def __init__(self) -> None:
        if pyplot.get_fignums():
            self._figure: Figure = pyplot.gcf()
            self._figure.clear()
        else:
            self._figure = pyplot.figure(dpi=300, figsize=figaspect(0.5))
        self._figure.subplots_adjust(wspace=0.25, left=0.1, right=0.95)
        self._axes_2d: Axes = self._figure.add_subplot(121)
        self._axes_3d: Axes3D = self._figure.add_subplot(122, projection="3d")
        self._axes_3d.tick_params(labelsize=5)
        self._axes_2d.tick_params(labelsize=5)
        self._axes_2d.set_xlabel("latitude")
        self._axes_3d.set_xlabel("latitude")
        self._axes_2d.set_ylabel("longitude")
        self._axes_3d.set_ylabel("longitude")
        self._axes_3d.set_zlabel("altitude")
        self._map_items = set()

    def add_item(self, item: MapItem) -> None:
        self._map_items.add(item)

    def clear(self) -> None:
        self._map_items.clear()

    def render(self, *, elevation: int = 30, azimuth: int = -130) -> None:
        if not self._map_items:
            print(" !! Politely refusing to render a map with no items.")
            return
        map_x_high, map_x_low, map_y_high, map_y_low, map_z_high, map_z_low = self._calculate_render_limits()

        for item in MapItem.sort_for_map_view(self._map_items):
            (item_x_low, item_x_high), (item_y_low, item_y_high), _ = item.limits
            if item.image:
                self._axes_2d.imshow(item.image, extent=[item_x_low, item_x_high, item_y_low, item_y_high])
            for x_data, y_data, z_data in item.line_data:
                self._axes_3d.plot3D(x_data, y_data, z_data, color=item.colour)
                self._axes_2d.plot(x_data, y_data, color=item.colour, linewidth=0.5)
            if item.label:
                self._axes_2d.text(avg(item_x_high, item_x_low), item_y_high, item.label, fontsize=3, ha="center", weight="light")

        self._axes_3d.view_init(elev=elevation, azim=azimuth)
        self._axes_3d.set_xlim3d(xmax=map_x_high, xmin=map_x_low)
        self._axes_3d.set_ylim3d(ymax=map_y_high, ymin=map_y_low)
        self._axes_3d.set_zlim3d(zmax=map_z_high, zmin=map_z_low)
        self._axes_2d.set_xlim(xmax=map_x_high, xmin=map_x_low)
        self._axes_2d.set_ylim(ymax=map_y_high, ymin=map_y_low)
        self._figure.show()

    def _calculate_render_limits(self):
        x_low, x_high, y_low, y_high, z_low, z_high = [None, None, None, None, None, None]
        for item in self._map_items:
            if x_high is None:
                (x_low, x_high), (y_low, y_high), (z_low, z_high) = item.limits
            else:
                x_limits, y_limits, z_limits = item.limits
                x_low = min(x_low, x_limits[0])
                x_high = max(x_high, x_limits[1])
                y_low = min(y_low, y_limits[0])
                y_high = max(y_high, y_limits[1])
                z_low = min(z_low, z_limits[0])
                z_high = max(z_high, z_limits[1])
        x_low -= (x_high - x_low) / 50
        x_high += (x_high - x_low) / 50
        y_low -= (y_high - y_low) / 50
        y_high += (y_high - y_low) / 30
        z_low -= (z_high - z_low) / 50
        z_high += (z_high - z_low) / 50
        x_delta = x_high - x_low
        y_delta = y_high - y_low
        if x_delta > y_delta:
            diff = x_delta - y_delta
            y_low -= diff / 2
            y_high += diff / 2
        else:
            diff = y_delta - x_delta
            x_low -= diff / 2
            x_high += diff / 2
        return x_high, x_low, y_high, y_low, z_high, z_low


def _randomize_colour(colour: Colour, *, delta: float = 0.25) -> Colour:
    r, g, b, a = colour
    return (
        max(0., min(1., r + uniform(-delta, delta))),
        max(0., min(1., g + uniform(-delta, delta))),
        max(0., min(1., b + uniform(-delta, delta))),
        a,
    )


def _generate_circle(lat_pos: float, lon_pos: float, alt_pos: float, radius: float) -> LineData:
    x_values = []
    y_values = []
    z_values = []
    for deg in range(361):
        x_values.append(lat_pos + sin(radians(deg)) * radius)
        y_values.append(lon_pos + cos(radians(deg)) * radius)
        z_values.append(alt_pos)
    return x_values, y_values, z_values


def _generate_octagon(lat: Range, lon: Range, alt: float) -> LineData:
    lat_mid_high = avg(lat.high, lat.high, lat.high, lat.low)
    lat_mid_low = avg(lat.high, lat.low, lat.low, lat.low)
    lon_mid_high = avg(lon.high, lon.high, lon.high, lon.low)
    lon_mid_low = avg(lon.high, lon.low, lon.low, lon.low)
    return _convert_to_line_data([
        (lat.low, lon_mid_low, alt),
        (lat.low, lon_mid_high, alt),
        (lat_mid_low, lon.high, alt),
        (lat_mid_high, lon.high, alt),
        (lat.high, lon_mid_high, alt),
        (lat.high, lon_mid_low, alt),
        (lat_mid_high, lon.low, alt),
        (lat_mid_low, lon.low, alt),
        (lat.low, lon_mid_low, alt),
    ])


def _generate_cuboid(
        lat_low: float, lat_high: float, lon_low: float, lon_high: float, alt_low: float, alt_high: float
) -> List[LineData]:
    line_data = []
    if lat_low == lat_high:
        line_data.append(_convert_to_line_data([
            (lat_low, lon_low, alt_low),
            (lat_low, lon_high, alt_low),
            (lat_low, lon_high, alt_high),
            (lat_low, lon_low, alt_high),
            (lat_low, lon_low, alt_low),
        ]))
    elif lon_low == lon_high:
        line_data.append(_convert_to_line_data([
            (lat_low, lon_low, alt_low),
            (lat_high, lon_low, alt_low),
            (lat_high, lon_low, alt_high),
            (lat_low, lon_low, alt_high),
            (lat_low, lon_low, alt_low),
        ]))
    elif alt_low == alt_high:
        line_data.append(_convert_to_line_data([
            (lat_low, lon_low, alt_low),
            (lat_high, lon_low, alt_low),
            (lat_high, lon_high, alt_low),
            (lat_low, lon_high, alt_low),
            (lat_low, lon_low, alt_low),
        ]))
    else:
        line_data.extend(_generate_cuboid(lat_low, lat_high, lon_low, lon_high, alt_low, alt_low))
        line_data.extend(_generate_cuboid(lat_low, lat_high, lon_low, lon_high, alt_high, alt_high))
        line_data.append(_convert_to_line_data([(lat_low, lon_low, alt_low), (lat_low, lon_low, alt_high)]))
        line_data.append(_convert_to_line_data([(lat_high, lon_low, alt_low), (lat_high, lon_low, alt_high)]))
        line_data.append(_convert_to_line_data([(lat_high, lon_high, alt_low), (lat_high, lon_high, alt_high)]))
        line_data.append(_convert_to_line_data([(lat_low, lon_high, alt_low), (lat_low, lon_high, alt_high)]))
    return line_data


def _convert_to_line_data(points: List[Point3D]) -> LineData:
    x_values = []
    y_values = []
    z_values = []
    for x, y, z in points:
        x_values.append(x)
        y_values.append(y)
        z_values.append(z)
    return x_values, y_values, z_values


def _main():
    map_view = MapView()
    map_view.add_item(CityMarker(Span(None, lat=Range(6315, 6330), lon=Range(8220, 8250), alt=Range(0.3), con=Range(0), rea={0})))
    map_view.render()
    map_view.render(elevation=90, azimuth=-90)
    map_view.render(elevation=60)
    map_view.render(elevation=80, azimuth=-180)
    map_view.render(elevation=10, azimuth=-180)


if __name__ == '__main__':
    _main()
