import numpy as np

from qgis.core import QgsRectangle


def get_intersection_extent(
    before_layer,
    after_layer
):
    """
    Определяет общую пространственную область
    двух растровых слоёв.
    """

    before_extent = before_layer.extent()
    after_extent = after_layer.extent()

    intersection = before_extent.intersect(
        after_extent
    )

    if intersection.isEmpty():
        raise ValueError(
            "Растровые слои не имеют "
            "общей пространственной области."
        )

    return intersection


def calculate_grid_size(
    extent,
    pixel_size_x,
    pixel_size_y
):
    """
    Рассчитывает размер общей растровой сетки.
    """

    width = round(
        extent.width() / pixel_size_x
    )

    height = round(
        extent.height() / pixel_size_y
    )

    if width <= 0 or height <= 0:
        raise ValueError(
            "Не удалось определить размер "
            "растровой сетки."
        )

    return width, height


def read_raster_extent(
    layer,
    band,
    extent,
    width,
    height
):
    """
    Читает выбранный канал растрового слоя
    в указанной пространственной области.

    Возвращает:
        array
        valid_mask
    """

    provider = layer.dataProvider()

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

    valid_mask = np.ones(
        (height, width),
        dtype=bool
    )

    for row in range(height):

        for column in range(width):

            value = block.value(
                row,
                column
            )

            array[row, column] = value

            try:
                is_nodata = block.isNoData(
                    row,
                    column
                )
            except Exception:
                is_nodata = False

            if is_nodata:
                valid_mask[row, column] = False

    # Дополнительная проверка на NaN
    valid_mask &= np.isfinite(array)

    return array, valid_mask


def save_change_mask(
    mask,
    output_path,
    extent,
    crs,
    pixel_size_x,
    pixel_size_y
):
    """
    Сохраняет маску изменений в GeoTIFF.

    Значения:
        0   - изменений нет
        1   - обнаружено изменение
        255 - NoData
    """

    from osgeo import gdal, osr

    height, width = mask.shape

    driver = gdal.GetDriverByName(
        "GTiff"
    )

    dataset = driver.Create(
        output_path,
        width,
        height,
        1,
        gdal.GDT_Byte
    )

    if dataset is None:
        raise ValueError(
            "Не удалось создать выходной GeoTIFF."
        )

    geotransform = (
        extent.xMinimum(),
        pixel_size_x,
        0.0,
        extent.yMaximum(),
        0.0,
        -pixel_size_y
    )

    dataset.SetGeoTransform(
        geotransform
    )

    spatial_reference = osr.SpatialReference()

    spatial_reference.ImportFromWkt(
        crs.toWkt()
    )

    dataset.SetProjection(
        spatial_reference.ExportToWkt()
    )

    band = dataset.GetRasterBand(1)

    band.WriteArray(mask)

    band.SetNoDataValue(255)

    band.FlushCache()

    dataset.FlushCache()

    dataset = None