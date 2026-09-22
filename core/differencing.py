import numpy as np


def calculate_difference(before_array, after_array):
    """
    Вычисляет абсолютную разницу между двумя растровыми массивами.

    Parameters
    ----------
    before_array : numpy.ndarray
        Массив значений первого снимка.

    after_array : numpy.ndarray
        Массив значений второго снимка.

    Returns
    -------
    numpy.ndarray
        Массив абсолютных разностей.
    """

    if before_array.shape != after_array.shape:
        raise ValueError(
            "Размеры растровых массивов не совпадают."
        )

    difference = np.abs(
        after_array.astype(float)
        - before_array.astype(float)
    )

    return difference


def calculate_threshold(difference, sigma=2.0):
    """
    Рассчитывает статистический порог изменений.

    Порог определяется по формуле:

        threshold = mean + sigma * std

    Parameters
    ----------
    difference : numpy.ndarray
        Массив абсолютных разностей.

    sigma : float
        Коэффициент стандартного отклонения.

    Returns
    -------
    tuple
        Среднее значение, стандартное отклонение и порог.
    """

    mean_value = np.mean(difference)
    std_value = np.std(difference)

    threshold = (
        mean_value
        + sigma * std_value
    )

    return (
        mean_value,
        std_value,
        threshold
    )


def create_change_mask(difference, threshold):
    """
    Создаёт бинарную маску изменений.

    Пиксели, для которых разница превышает
    порог, получают значение 1.
    Остальные получают значение 0.
    """

    mask = (
        difference > threshold
    ).astype(np.uint8)

    return mask