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

    keep[0] = False

    filtered_mask = keep[
        labeled
    ].astype(np.uint8)

    return filtered_mask


def create_qa_valid_mask(
    qa_array
):
    """
    Создаёт маску валидных пикселей
    на основе Landsat Collection 2 QA_PIXEL.

    Для Landsat 8-9 используются следующие
    биты QA_PIXEL:

        bit 0 - Fill
        bit 1 - Dilated Cloud
        bit 2 - Cirrus
        bit 3 - Cloud
        bit 4 - Cloud Shadow
        bit 5 - Snow

    Если хотя бы один из этих битов установлен,
    пиксель исключается из анализа.

    Возвращает:
        True  - пиксель можно использовать
        False - пиксель необходимо исключить
    """

    qa_array = (
        qa_array
        .astype(np.uint64)
    )

    # ---------------------------------------------------------
    # Битовые маски
    # ---------------------------------------------------------

    fill = (
        (qa_array & (1 << 0)) != 0
    )

    dilated_cloud = (
        (qa_array & (1 << 1)) != 0
    )

    cirrus = (
        (qa_array & (1 << 2)) != 0
    )

    cloud = (
        (qa_array & (1 << 3)) != 0
    )

    cloud_shadow = (
        (qa_array & (1 << 4)) != 0
    )

    snow = (
        (qa_array & (1 << 5)) != 0
    )

    # ---------------------------------------------------------
    # Объединяем все плохие пиксели
    # ---------------------------------------------------------

    invalid = (
        fill
        | dilated_cloud
        | cirrus
        | cloud
        | cloud_shadow
        | snow
    )

    valid = ~invalid

    return valid


def validate_qa_layer(
    qa_layer,
    reference_layer,
    name
):
    """
    Проверяет QA-слой.
    """

    if qa_layer is None:

        raise ValueError(
            f"Не выбран QA_PIXEL для "
            f"{name}."
        )

    if not qa_layer.isValid():

        raise ValueError(
            f"QA-слой «{qa_layer.name()}» "
            f"недействителен."
        )

    if qa_layer.bandCount() < 1:

        raise ValueError(
            f"QA-слой «{qa_layer.name()}» "
            f"не содержит каналов."
        )

    if qa_layer.crs() != reference_layer.crs():

        raise ValueError(
            f"Система координат QA-слоя "
            f"«{qa_layer.name()}» не совпадает "
            f"с системой координат снимка."
        )


def detect_changes(
    before_layer,
    after_layer,
    band,
    sigma,
    min_region_size,
    output_path,
    before_qa_layer=None,
    after_qa_layer=None
):
    """
    Полный алгоритм обнаружения изменений.

    Этапы:

        1. Определение общей области.
        2. Формирование общей сетки.
        3. Чтение основных растров.
        4. Чтение QA_PIXEL.
        5. Создание масок облаков и других
           непригодных пикселей.
        6. Исключение NoData и QA-пикселей.
        7. Вычисление абсолютной разности.
        8. Расчёт статистического порога.
        9. Формирование бинарной маски.
        10. Удаление мелких областей.
        11. Сохранение GeoTIFF.

    Возвращает словарь со статистикой.
    """

    # =========================================================
    # 1. Общая пространственная область
    # =========================================================

    extent = get_intersection_extent(
        before_layer,
        after_layer
    )

    # =========================================================
    # 2. Общая сетка
    # =========================================================

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

    # =========================================================
    # 3. Чтение основных растров
    # =========================================================

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

    # =========================================================
    # 4. Базовая маска валидных пикселей
    # =========================================================

    valid_pixels = (
        before_valid
        & after_valid
    )

    # =========================================================
    # 5. QA_PIXEL
    # =========================================================

    qa_masked_pixels = 0

    if (
        before_qa_layer is not None
        and after_qa_layer is not None
    ):

        # -----------------------------------------------------
        # Проверяем QA
        # -----------------------------------------------------

        validate_qa_layer(
            before_qa_layer,
            before_layer,
            "снимка до"
        )

        validate_qa_layer(
            after_qa_layer,
            after_layer,
            "снимка после"
        )

        # -----------------------------------------------------
        # Читаем QA до
        # -----------------------------------------------------

        before_qa_array, before_qa_valid = (
            read_raster_extent(
                before_qa_layer,
                1,
                extent,
                width,
                height
            )
        )

        # -----------------------------------------------------
        # Читаем QA после
        # -----------------------------------------------------

        after_qa_array, after_qa_valid = (
            read_raster_extent(
                after_qa_layer,
                1,
                extent,
                width,
                height
            )
        )

        # -----------------------------------------------------
        # Создаём маски чистых пикселей
        # -----------------------------------------------------

        before_qa_clear = (
            create_qa_valid_mask(
                before_qa_array
            )
        )

        after_qa_clear = (
            create_qa_valid_mask(
                after_qa_array
            )
        )

        # -----------------------------------------------------
        # QA также должен быть валидным
        # -----------------------------------------------------

        qa_valid = (
            before_qa_valid
            & after_qa_valid
            & before_qa_clear
            & after_qa_clear
        )

        # -----------------------------------------------------
        # Считаем количество исключённых пикселей
        # -----------------------------------------------------

        qa_masked_pixels = int(
            np.sum(
                valid_pixels
                & ~qa_valid
            )
        )

        # -----------------------------------------------------
        # Добавляем QA к общей маске
        # -----------------------------------------------------

        valid_pixels = (
            valid_pixels
            & qa_valid
        )

    # =========================================================
    # 6. Проверка количества валидных пикселей
    # =========================================================

    valid_count = int(
        np.sum(valid_pixels)
    )

    if valid_count == 0:

        raise ValueError(
            "После исключения NoData и "
            "QA_PIXEL не осталось "
            "валидных пикселей."
        )

    # =========================================================
    # 7. Вычисление разности
    # =========================================================

    difference = calculate_difference(
        before_array,
        after_array
    )

    # =========================================================
    # 8. Статистический порог
    # =========================================================

    valid_difference = difference[
        valid_pixels
    ]

    mean_value, std_value, threshold = (
        calculate_threshold(
            valid_difference,
            sigma
        )
    )

    # =========================================================
    # 9. Бинарная маска
    # =========================================================

    raw_mask = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    raw_mask[
        valid_pixels
    ] = create_change_mask(
        difference[
            valid_pixels
        ],
        threshold
    )

    # =========================================================
    # 10. Удаление мелких областей
    # =========================================================

    filtered_mask = remove_small_regions(
        raw_mask,
        min_region_size
    )

    # =========================================================
    # 11. Возвращаем NoData
    # =========================================================

    filtered_mask[
        ~valid_pixels
    ] = 255

    # =========================================================
    # 12. Сохранение
    # =========================================================

    save_change_mask(
        filtered_mask,
        output_path,
        extent,
        before_layer.crs(),
        pixel_size_x,
        pixel_size_y
    )

    # =========================================================
    # 13. Статистика
    # =========================================================

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

    # =========================================================
    # 14. Возвращаем результат
    # =========================================================

    return {

        "width": width,

        "height": height,

        "valid_pixels": valid_count,

        "nodata_pixels": nodata_count,

        "qa_masked_pixels": (
            qa_masked_pixels
        ),

        "mean": float(
            mean_value
        ),

        "std": float(
            std_value
        ),

        "threshold": float(
            threshold
        ),

        "changed_before_filter": (
            changed_before
        ),

        "changed_after_filter": (
            changed_after
        ),

        "output_path": output_path
    }