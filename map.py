from abc import ABC, abstractmethod
from math import cos, sin, radians
from typing import Tuple, List, Optional, Any

from matplotlib import pyplot
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import is_color_like


class Drawable(ABC):
    @abstractmethod
    def to_3d_data(self) -> Tuple[List[float], List[float], List[float]]:
        pass


class Circle(Drawable):
    _lat_pos: float
    _lon_pos: float
    _alt_pos: float
    _radius: float

    def __init__(self, lat_pos: float, lon_pos: float, alt_pos: float, radius: float) -> None:
        self._lat_pos = lat_pos
        self._lon_pos = lon_pos
        self._alt_pos = alt_pos
        self._radius = radius

    def to_3d_data(self) -> Tuple[List[float], List[float], List[float]]:
        x_values = []
        y_values = []
        z_values = []
        for deg in range(361):
            x_values.append(self._lat_pos + sin(radians(deg)) * self._radius)
            y_values.append(self._lon_pos + cos(radians(deg)) * self._radius)
            z_values.append(self._alt_pos)
        return x_values, y_values, z_values


class RectangularCuboid(Drawable):
    _lat_low: float
    _lat_high: float
    _lon_low: float
    _lon_high: float
    _alt_low: float
    _alt_high: float

    def __init__(
            self, lat_low: float, lon_low: float, alt_low: float,
            lat_high: Optional[float] = None, lon_high: Optional[float] = None, alt_high: Optional[float] = None,
            *, lat_length: Optional[float] = None, lon_width: Optional[float] = None, alt_depth: Optional[float] = None
    ) -> None:
        if (lat_high is None) == (lat_length is None):
            raise ValueError("Either lat_high or lat_length must be provided (not both)")
        if (lon_high is None) == (lon_width is None):
            raise ValueError("Either lon_high or lon_width must be provided (not both)")
        if (alt_high is None) == (alt_depth is None):
            raise ValueError("Either alt_high or alt_depth must be provided (not both)")
        self._lat_low = lat_low
        self._lon_low = lon_low
        self._alt_low = alt_low
        self._lat_high = lat_high if lat_high is not None else lat_low + lat_length
        self._lon_high = lon_high if lon_high is not None else lon_low + lon_width
        self._alt_high = alt_high if alt_high is not None else alt_low + alt_depth

    def to_3d_data(self) -> Tuple[List[float], List[float], List[float]]:
        x_values = []
        y_values = []
        z_values = []
        for x, y, z in [
            (self._lat_low, self._lon_low, self._alt_low),
            (self._lat_low, self._lon_high, self._alt_low),
            (self._lat_low, self._lon_high, self._alt_high),
            (self._lat_low, self._lon_low, self._alt_high),
            (self._lat_low, self._lon_low, self._alt_low),
            (self._lat_high, self._lon_low, self._alt_low),
            (self._lat_high, self._lon_high, self._alt_low),
            (self._lat_high, self._lon_high, self._alt_high),
            (self._lat_high, self._lon_low, self._alt_high),
            (self._lat_high, self._lon_low, self._alt_low),
            (self._lat_high, self._lon_high, self._alt_low),
            (self._lat_low, self._lon_high, self._alt_low),
            (self._lat_low, self._lon_high, self._alt_high),
            (self._lat_high, self._lon_high, self._alt_high),
            (self._lat_high, self._lon_low, self._alt_high),
            (self._lat_low, self._lon_low, self._alt_high),
        ]:
            x_values.append(x)
            y_values.append(y)
            z_values.append(z)
        return x_values, y_values, z_values


class MapView:
    _figure: Figure
    _axes: Axes3D

    def __init__(self) -> None:
        self._figure = pyplot.figure(dpi=300)
        self._axes: Axes3D = self._figure.add_subplot(projection="3d")
        self._axes.tick_params(labelsize=5)
        self._axes.set_xlabel("latitude")
        self._axes.set_ylabel("longitude")
        self._axes.set_zlabel("altitude")

    def render(self, *, elevation: int = 30, azimuth: int = -130) -> None:
        if elevation > 45:
            self._axes.xaxis.set_tick_params(pad=10, labelrotation=azimuth + 180)
            self._axes.yaxis.set_tick_params(pad=1, labelrotation=azimuth + 90)
        else:
            self._axes.xaxis.set_tick_params(pad=-5, labelrotation=azimuth+90)
            self._axes.yaxis.set_tick_params(pad=-5, labelrotation=azimuth-180)
        self._axes.set_zlim3d()
        self._axes.view_init(elev=elevation, azim=azimuth)
        self._figure.show()

    def draw(self, drawable: Drawable, colour: Any) -> None:
        if not is_color_like(colour):
            raise ValueError("Provided colour arg is invalid")
        x_data, y_data, z_data = drawable.to_3d_data()
        self._axes.plot3D(x_data, y_data, z_data, colour)

    def clear(self) -> None:
        self._axes.clear()


def _main():
    map_view = MapView()
    map_view.draw(RectangularCuboid(.2, .2, .2, .6, .7, .8), "green")
    map_view.draw(Circle(0.4, 0.3, 0.5, 0.25), "blue")
    map_view.render(elevation=60)
    map_view.render(elevation=80, azimuth=-180)
    map_view.render(elevation=10, azimuth=-180)


if __name__ == '__main__':
    _main()
