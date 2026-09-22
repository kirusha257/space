import numpy as np

from .differencing import (
    calculate_difference,
    calculate_threshold,
    create_change_mask
)

from .raster_preparation import (
    get_intersection_extent,
    calculate_grid_size,
    read_raster_extent,
    save_change_mask
)


def remove_small_regions(
    mask,
    min_size
):
    """
    Удаляет небольшие отдельные области
    изменений.

    min_size задаётся в пикселях.

    Возвращает очищенную бинарную маску.
    """

    from scipy import ndimage

    structure = np.ones(
        (3, 3),
        dtype=np.uint8
    )

    labeled, number = ndimage.label(
        mask == 1,
        structure=structure
    )

    if number == 0:
        return mask.copy()

    sizes = np.bincount(
        labeled.ravel()
    )

    keep = sizes >= min_size

    # Нулевая область является фоном
    keep[0] = False

    filtered_mask = keep[
        labeled
    ].astype(np.uint8)

    return filtered_mask


def detect_changes(
    before_layer,
    after_layer,
    band,
    sigma,
    min_region_size,
    output_path
):
    """
    Полный алгоритм обнаружения изменений.

    Этапы:
        1. Определение общей области.
        2. Формирование общей сетки.
        3. Чтение выбранного канала.
        4. Исключение NoData.
        5. Вычисление абсолютной разности.
        6. Расчёт статистического порога.
        7. Формирование бинарной маски.
        8. Удаление мелких областей.
        9. Сохранение GeoTIFF.

    Возвращает словарь со статистикой.
    """

    # -------------------------------------------------
    # 1. Общая пространственная область
    # -------------------------------------------------

    extent = get_intersection_extent(
        before_layer,
        after_layer
    )

    # -------------------------------------------------
    # 2. Общая сетка
    # -------------------------------------------------

    pixel_size_x = (
        before_layer.rasterUnitsPerPixelX()
    )

    pixel_size_y = (
        before_layer.rasterUnitsPerPixelY()
    )

    if pixel_size_x <= 0:
        raise ValueError(
            "Некорректный размер пикселя по X."
        )

    if pixel_size_y <= 0:
        raise ValueError(
            "Некорректный размер пикселя по Y."
        )

    width, height = calculate_grid_size(
        extent,
        pixel_size_x,
        pixel_size_y
    )

    # -------------------------------------------------
    # 3. Чтение растров
    # -------------------------------------------------

    before_array, before_valid = (
        read_raster_extent(
            before_layer,
            band,
            extent,
            width,
            height
        )
    )

    after_array, after_valid = (
        read_raster_extent(
            after_layer,
            band,
            extent,
            width,
            height
        )
    )

    # -------------------------------------------------
    # 4. Общая маска валидных пикселей
    # -------------------------------------------------

    valid_pixels = (
        before_valid
        & after_valid
    )

    valid_count = int(
        np.sum(valid_pixels)
    )

    if valid_count == 0:
        raise ValueError(
            "После исключения NoData "
            "не осталось валидных пикселей."
        )

    # -------------------------------------------------
    # 5. Вычисление разности
    # -------------------------------------------------

    difference = calculate_difference(
        before_array,
        after_array
    )

    # -------------------------------------------------
    # 6. Статистический порог
    # -------------------------------------------------

    valid_difference = difference[
        valid_pixels
    ]

    mean_value, std_value, threshold = (
        calculate_threshold(
            valid_difference,
            sigma
        )
    )

    # -------------------------------------------------
    # 7. Бинарная маска
    # -------------------------------------------------

    raw_mask = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    raw_mask[
        valid_pixels
    ] = create_change_mask(
        difference[valid_pixels],
        threshold
    )

    # -------------------------------------------------
    # 8. Удаление мелких областей
    # -------------------------------------------------

    filtered_mask = remove_small_regions(
        raw_mask,
        min_region_size
    )

    # Добавляем NoData обратно
    filtered_mask[
        ~valid_pixels
    ] = 255

    # -------------------------------------------------
    # 9. Сохранение
    # -------------------------------------------------

    save_change_mask(
        filtered_mask,
        output_path,
        extent,
        before_layer.crs(),
        pixel_size_x,
        pixel_size_y
    )

    # -------------------------------------------------
    # Статистика
    # -------------------------------------------------

    changed_before = int(
        np.sum(
            raw_mask == 1
        )
    )

    changed_after = int(
        np.sum(
            filtered_mask == 1
        )
    )

    nodata_count = int(
        np.sum(
            filtered_mask == 255
        )
    )

    return {
        "width": width,
        "height": height,
        "valid_pixels": valid_count,
        "nodata_pixels": nodata_count,
        "mean": float(mean_value),
        "std": float(std_value),
        "threshold": float(threshold),
        "changed_before_filter": changed_before,
        "changed_after_filter": changed_after,
        "output_path": output_path
    }