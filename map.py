from abc import ABC, abstractmethod
from math import cos, sin, radians
from random import uniform
from typing import Tuple, List, Optional, Set

from PIL.Image import Image
from matplotlib import pyplot
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure, figaspect
from mpl_toolkits.mplot3d import Axes3D

from util import avg, Span, Range

LineData = Tuple[List[float], List[float], List[float]]
Colour = Tuple[float, float, float, float]
AxesLimit = Tuple[float, float]
Point3D = Tuple[float, float, float]


class Colours:
    Blue: Colour = (0., 0., 1., 1.)
    Green: Colour = (0., 1., 0., 1.)
    Black: Colour = (0., 0., 0., 1.)


class _MapItem(ABC):
    _span: Span
    _image: Image
    _colour: Colour

    def __init__(self, span: Span, *, image: Image = None, colour: Colour = Colours.Black) -> None:
        self._span = span
        self._image = image
        self._colour = colour

    @property
    def colour(self) -> Colour:
        return self._colour

    @property
    def image(self) -> Optional[Image]:
        return self._image

    @property
    @abstractmethod
    def line_data(self) -> List[LineData]:
        pass

    @property
    def limits(self) -> Tuple[AxesLimit, AxesLimit, AxesLimit]:
        return (
            (self._span.latitude.low, self._span.latitude.high),
            (self._span.longitude.low, self._span.longitude.high),
            (self._span.altitude.low, self._span.altitude.high),
        )


class CityMarker(_MapItem):
    @property
    def line_data(self) -> List[LineData]:
        lat_mid = avg(self._span.latitude.low, self._span.latitude.high)
        lon_mid = avg(self._span.longitude.low, self._span.longitude.high)
        radius = avg(self._span.latitude.high - self._span.latitude.low, self._span.latitude.high - self._span.latitude.low) / 2
        return [
            _generate_circle(lat_mid, lon_mid, self._span.altitude.low, radius),
        ]

    def __init__(self, span: Span, *, colour: Colour = Colours.Blue, image: Image = None) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        colour_mutated = _randomize_colour(colour)
        super(CityMarker, self).__init__(span, colour=colour_mutated, image=image)


class BuildingMarker(_MapItem):
    @property
    def line_data(self) -> List[LineData]:
        return _generate_cuboid(
            self._span.latitude.low, self._span.latitude.high,
            self._span.longitude.low, self._span.longitude.high,
            self._span.altitude.low, self._span.altitude.high
        )

    def __init__(self, span: Span, *, colour: Colour = Colours.Green, image: Image = None) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        colour_mutated = _randomize_colour(colour)
        super(BuildingMarker, self).__init__(span, colour=colour_mutated, image=image)


class MapView:
    _figure: Figure
    _axes_3d: Axes3D
    _axes_2d: Axes
    _map_items: Set[_MapItem]

    def __init__(self) -> None:
        self._figure = pyplot.figure(dpi=300, figsize=figaspect(0.5))
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

    def add_item(self, item: _MapItem) -> None:
        self._map_items.add(item)

    def clear(self) -> None:
        self._map_items.clear()

    def render(self, *, elevation: int = 30, azimuth: int = -130) -> None:
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
            for x_data, y_data, z_data in item.line_data:
                self._axes_3d.plot3D(x_data, y_data, z_data, color=item.colour)
                self._axes_2d.plot(x_data, y_data, color=item.colour)

        x_low -= (x_high - x_low) / 20
        x_high += (x_high - x_low) / 20
        y_low -= (y_high - y_low) / 20
        y_high += (y_high - y_low) / 20
        z_low -= (z_high - z_low) / 20
        z_high += (z_high - z_low) / 20

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

        self._axes_3d.view_init(elev=elevation, azim=azimuth)
        self._axes_3d.set_xlim3d(xmax=x_high, xmin=x_low)
        self._axes_3d.set_ylim3d(ymax=y_high, ymin=y_low)
        self._axes_3d.set_zlim3d(zmax=z_high, zmin=z_low)
        self._axes_2d.set_xlim(xmax=x_high, xmin=x_low)
        self._axes_2d.set_ylim(ymax=y_high, ymin=y_low)
        self._figure.show()


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


def _generate_octagon(
        lat_low: float, lat_high: float, lon_low: float, lon_high: float, alt: float
) -> LineData:
    lat_mid_high = avg(lat_high, lat_high, lat_low)
    lat_mid_low = avg(lat_high, lat_low, lat_low)
    lon_mid_high = avg(lon_high, lat_high, lon_low)
    lon_mid_low = avg(lon_high, lon_low, lat_low)
    line_data = _convert_to_line_data([
        (lat_low, lon_mid_low, alt),
        (lat_low, lon_mid_high, alt),
        (lat_mid_low, lon_high, alt),
        (lat_mid_high, lon_high, alt),
        (lat_high, lon_mid_high, alt),
        (lat_high, lon_mid_low, alt),
        (lat_mid_high, lon_low, alt),
        (lat_mid_low, lon_low, alt),
        (lat_low, lon_mid_low, alt),
    ])
    return line_data


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
