import numpy as np


def read_raster_band(layer, band):
    """
    Читает выбранный канал растрового слоя
    и возвращает его значения в виде NumPy-массива.

    Parameters
    ----------
    layer : QgsRasterLayer
        Растровый слой QGIS.

    band : int
        Номер канала.

    Returns
    -------
    numpy.ndarray
        Двумерный массив значений пикселей.
    """

    provider = layer.dataProvider()

    width = layer.width()
    height = layer.height()
    extent = layer.extent()

    block = provider.block(
        band,
        extent,
        width,
        height
    )

    if block is None:
        raise ValueError(
            f"Не удалось прочитать канал {band} "
            f"слоя «{layer.name()}»."
        )

    array = np.zeros(
        (height, width),
        dtype=np.float64
    )

    for row in range(height):
        for column in range(width):

            value = block.value(
                row,
                column
            )

            array[row, column] = value

    return array