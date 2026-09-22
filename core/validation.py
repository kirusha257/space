from qgis.core import QgsRasterLayer


def validate_rasters(
    before_layer,
    after_layer,
    band
):
    """
    Проверяет, можно ли использовать два
    растровых слоя для попиксельного сравнения.

    Различия в размере, охвате и разрешении
    допускаются: далее растры будут приведены
    к общей пространственной сетке.

    Возвращает:
        (True, сообщение)
    или
        (False, сообщение)
    """

    if not isinstance(before_layer, QgsRasterLayer):
        return (
            False,
            "Слой «Снимок до» не является растровым."
        )

    if not isinstance(after_layer, QgsRasterLayer):
        return (
            False,
            "Слой «Снимок после» не является растровым."
        )

    if not before_layer.isValid():
        return (
            False,
            f"Растр «{before_layer.name()}» недействителен."
        )

    if not after_layer.isValid():
        return (
            False,
            f"Растр «{after_layer.name()}» недействителен."
        )

    if before_layer == after_layer:
        return (
            False,
            "Необходимо выбрать два разных "
            "растровых слоя."
        )

    if band is None or band < 1:
        return (
            False,
            "Номер канала должен быть больше нуля."
        )

    if band > before_layer.bandCount():
        return (
            False,
            f"В растровом слое «{before_layer.name()}» "
            f"нет канала {band}."
        )

    if band > after_layer.bandCount():
        return (
            False,
            f"В растровом слое «{after_layer.name()}» "
            f"нет канала {band}."
        )

    if before_layer.crs() != after_layer.crs():
        return (
            False,
            "Системы координат растров не совпадают.\n\n"
            f"Снимок до: "
            f"{before_layer.crs().authid()}\n"
            f"Снимок после: "
            f"{after_layer.crs().authid()}\n\n"
            "Перед сравнением необходимо привести "
            "растры к одной системе координат."
        )

    before_extent = before_layer.extent()
    after_extent = after_layer.extent()

    intersection = before_extent.intersect(
        after_extent
    )

    if intersection.isEmpty():
        return (
            False,
            "Растровые слои не имеют общей "
            "пространственной области."
        )

    return (
        True,
        "Растры совместимы для анализа. "
        "Общая область и пространственная сетка "
        "будут определены автоматически."
    )