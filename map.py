from abc import ABC, abstractmethod
from math import cos, sin, radians
from random import uniform
from typing import Tuple, List, Optional, Any, Set

from PIL.Image import Image
from matplotlib import pyplot
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure, figaspect
from mpl_toolkits.mplot3d import Axes3D

LineData = Tuple[List[float], List[float], List[float]]
Colour = Tuple[float, float, float, float]
AxesLimit = Tuple[float, float]
Point3D = Tuple[float, float, float]


class Colours:
    Blue: Colour = (0., 0., 1., 1.)
    Green: Colour = (0., 1., 0., 1.)


class _MapItem(ABC):
    @property
    @abstractmethod
    def colour(self) -> Any:
        pass

    @property
    @abstractmethod
    def image(self) -> Optional[Image]:
        pass

    @property
    @abstractmethod
    def line_data(self) -> List[LineData]:
        pass

    @property
    @abstractmethod
    def limits(self) -> Tuple[AxesLimit, AxesLimit, AxesLimit]:
        pass


class CityMarker(_MapItem):
    _lat_pos: float
    _lon_pos: float
    _alt_pos: float
    _radius: float
    _colour: Any
    _image: Optional[Image]

    @property
    def colour(self) -> Any:
        return self._colour

    @property
    def image(self) -> Optional[Image]:
        return self._image

    @property
    def line_data(self) -> List[LineData]:
        return [
            _generate_circle(self._lat_pos, self._lon_pos, self._alt_pos, self._radius)
        ]

    @property
    def limits(self) -> Tuple[AxesLimit, AxesLimit, AxesLimit]:
        return (
            (self._lat_pos - self._radius, self._lat_pos + self._radius),
            (self._lon_pos - self._radius, self._lon_pos + self._radius),
            (self._alt_pos, self._alt_pos + 1),
        )

    def __init__(self, lat_pos: float, lon_pos: float, alt_pos: float, radius: float,
                 *, colour: Colour = Colours.Blue) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        self._lat_pos = lat_pos
        self._lon_pos = lon_pos
        self._alt_pos = alt_pos
        self._radius = radius
        self._colour = _randomize_colour(colour)


class BuildingMarker(_MapItem):
    _lat_low: float
    _lat_high: float
    _lon_low: float
    _lon_high: float
    _alt_low: float
    _alt_high: float
    _colour: Any
    _image: Optional[Image]

    @property
    def colour(self) -> Any:
        return self._colour

    @property
    def image(self) -> Optional[Image]:
        return self._image

    @property
    def line_data(self) -> List[LineData]:
        return _generate_cuboid(self._lat_low, self._lat_high, self._lon_low, self._lon_high, self._alt_low, self._alt_high)

    @property
    def limits(self) -> Tuple[AxesLimit, AxesLimit, AxesLimit]:
        return (
            (self._lat_low, self._lat_high),
            (self._lon_low, self._lon_high),
            (self._alt_low, self._alt_high),
        )

    def __init__(self, lat_low: float, lat_high: float, lon_low: float, lon_high: float, alt_low: float, alt_high: float,
                 *, colour: Colour = Colours.Green) -> None:
        if not is_color_like(colour):
            raise ValueError(f"Provided colour '{colour}' could not be interpreted")
        self._lat_low = lat_low
        self._lat_high = lat_high
        self._lon_low = lon_low
        self._lon_high = lon_high
        self._alt_low = alt_low
        self._alt_high = alt_high
        self._colour = _randomize_colour(colour)


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
    map_view.add_item(CityMarker(6325, 8229, 0.3, 7.4))
    map_view.render()
    map_view.render(elevation=90, azimuth=-90)
    map_view.render(elevation=60)
    map_view.render(elevation=80, azimuth=-180)
    map_view.render(elevation=10, azimuth=-180)


if __name__ == '__main__':
    _main()
