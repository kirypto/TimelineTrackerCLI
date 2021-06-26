from matplotlib import pyplot
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D


class MapView:
    _figure: Figure
    _axes: Axes3D

    def __init__(self) -> None:
        self._figure = pyplot.figure()
        self._axes: Axes3D = self._figure.add_subplot(projection="3d")

    def display(self, *, elevation: int = 60, azimuth: int = 5) -> None:
        self._axes.view_init(elev=elevation, azim=azimuth)
        self._figure.show()


def _main():
    map_view = MapView()
    map_view.display()


if __name__ == '__main__':
    _main()
