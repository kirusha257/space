import os

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QLineEdit,
    QFileDialog
)

from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsRasterLayer,
    QgsProject,
    QgsRasterShader,
    QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer
)

from ..core.validation import validate_rasters
from ..core.detection import detect_changes


class ChangeDetectorDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)

        self.iface = iface

        self.setWindowTitle(
            "Детектор изменений растров"
        )

        self.setMinimumWidth(520)

        self.create_ui()

        self.load_raster_layers()

    # ---------------------------------------------------------
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # ---------------------------------------------------------

    def create_ui(self):

        main_layout = QVBoxLayout()

        # -----------------------------------------------------
        # Исходные растры
        # -----------------------------------------------------

        raster_group = QGroupBox(
            "Исходные растры"
        )

        raster_layout = QFormLayout()

        self.before_combo = QComboBox()
        self.after_combo = QComboBox()

        raster_layout.addRow(
            "Снимок до:",
            self.before_combo
        )

        raster_layout.addRow(
            "Снимок после:",
            self.after_combo
        )

        raster_group.setLayout(
            raster_layout
        )

        main_layout.addWidget(
            raster_group
        )

        # -----------------------------------------------------
        # Параметры анализа
        # -----------------------------------------------------

        parameter_group = QGroupBox(
            "Параметры анализа"
        )

        parameter_layout = QFormLayout()

        # Канал

        self.band_combo = QComboBox()

        parameter_layout.addRow(
            "Канал:",
            self.band_combo
        )

        # Sigma

        self.sigma_spin = QDoubleSpinBox()

        self.sigma_spin.setMinimum(
            0.1
        )

        self.sigma_spin.setMaximum(
            10.0
        )

        self.sigma_spin.setSingleStep(
            0.1
        )

        self.sigma_spin.setValue(
            2.0
        )

        self.sigma_spin.setSuffix(
            " σ"
        )

        parameter_layout.addRow(
            "Статистический порог:",
            self.sigma_spin
        )

        # Минимальный размер области

        self.min_region_spin = QSpinBox()

        self.min_region_spin.setMinimum(
            1
        )

        self.min_region_spin.setMaximum(
            1000000
        )

        self.min_region_spin.setValue(
            100
        )

        self.min_region_spin.setSuffix(
            " пикс."
        )

        parameter_layout.addRow(
            "Мин. размер области:",
            self.min_region_spin
        )

        parameter_group.setLayout(
            parameter_layout
        )

        main_layout.addWidget(
            parameter_group
        )

        # -----------------------------------------------------
        # Результат
        # -----------------------------------------------------

        output_group = QGroupBox(
            "Результат"
        )

        output_layout = QFormLayout()

        self.output_edit = QLineEdit()

        self.output_edit.setText(
            os.path.join(
                os.path.expanduser("~"),
                "Desktop",
                "change_mask.tif"
            )
        )

        self.output_button = QPushButton(
            "Выбрать..."
        )

        self.output_button.clicked.connect(
            self.select_output
        )

        output_layout.addRow(
            "Файл маски:",
            self.output_edit
        )

        output_layout.addRow(
            "",
            self.output_button
        )

        output_group.setLayout(
            output_layout
        )

        main_layout.addWidget(
            output_group
        )

        # -----------------------------------------------------
        # Кнопка запуска
        # -----------------------------------------------------

        self.run_button = QPushButton(
            "Определить изменения"
        )

        self.run_button.clicked.connect(
            self.run_detection
        )

        main_layout.addWidget(
            self.run_button
        )

        # -----------------------------------------------------
        # Статус
        # -----------------------------------------------------

        self.status_label = QLabel(
            "Выберите два растровых слоя."
        )

        self.status_label.setWordWrap(
            True
        )

        main_layout.addWidget(
            self.status_label
        )

        self.setLayout(
            main_layout
        )

        # При смене первого растра
        # обновляем список каналов

        self.before_combo.currentIndexChanged.connect(
            self.update_bands
        )

    # ---------------------------------------------------------
    # ЗАГРУЗКА РАСТРОВЫХ СЛОЁВ
    # ---------------------------------------------------------

    def load_raster_layers(self):

        self.before_combo.clear()

        self.after_combo.clear()

        layers = (
            self.iface
            .mapCanvas()
            .layers()
        )

        raster_layers = [
            layer
            for layer in layers
            if isinstance(
                layer,
                QgsRasterLayer
            )
            and layer.isValid()
        ]

        for layer in raster_layers:

            self.before_combo.addItem(
                layer.name(),
                layer
            )

            self.after_combo.addItem(
                layer.name(),
                layer
            )

        self.update_bands()

    # ---------------------------------------------------------
    # ОБНОВЛЕНИЕ СПИСКА КАНАЛОВ
    # ---------------------------------------------------------

    def update_bands(self):

        self.band_combo.clear()

        layer = (
            self.before_combo
            .currentData()
        )

        if layer is None:
            return

        band_count = (
            layer.bandCount()
        )

        provider = (
            layer.dataProvider()
        )

        for band_number in range(
            1,
            band_count + 1
        ):

            description = (
                provider.generateBandName(
                    band_number
                )
            )

            if description:

                text = (
                    f"{band_number} - "
                    f"{description}"
                )

            else:

                text = (
                    f"Канал "
                    f"{band_number}"
                )

            self.band_combo.addItem(
                text,
                band_number
            )

    # ---------------------------------------------------------
    # ВЫБОР ФАЙЛА РЕЗУЛЬТАТА
    # ---------------------------------------------------------

    def select_output(self):

        path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Сохранить маску изменений",
                self.output_edit.text(),
                "GeoTIFF (*.tif *.tiff)"
            )
        )

        if path:

            self.output_edit.setText(
                path
            )

    # ---------------------------------------------------------
    # НАСТРОЙКА ОТОБРАЖЕНИЯ МАСКИ
    # ---------------------------------------------------------

    def style_change_layer(
        self,
        layer
    ):
        """
        Настраивает отображение результата.

        Значения растра:

            0   - изменений нет
            1   - обнаружено изменение
            255 - NoData

        Отображение:

            0   - прозрачный
            1   - красный
            255 - прозрачный
        """

        # Создаём цветовую шкалу

        color_ramp = (
            QgsColorRampShader()
        )

        color_ramp.setColorRampType(
            QgsColorRampShader.Discrete
        )

        # ---------------------------------------------
        # Значение 0
        # ---------------------------------------------

        no_change = (
            QgsColorRampShader.ColorRampItem(
                0,
                QColor(
                    0,
                    0,
                    0,
                    0
                ),
                "Нет изменений"
            )
        )

        # ---------------------------------------------
        # Значение 1
        # ---------------------------------------------

        change = (
            QgsColorRampShader.ColorRampItem(
                1,
                QColor(
                    255,
                    0,
                    0,
                    255
                ),
                "Изменение"
            )
        )

        color_ramp.setColorRampItemList(
            [
                no_change,
                change
            ]
        )

        # ---------------------------------------------
        # Создаём shader
        # ---------------------------------------------

        raster_shader = (
            QgsRasterShader()
        )

        raster_shader.setRasterShaderFunction(
            color_ramp
        )

        # ---------------------------------------------
        # Создаём renderer
        # ---------------------------------------------

        renderer = (
            QgsSingleBandPseudoColorRenderer(
                layer.dataProvider(),
                1,
                raster_shader
            )
        )

        layer.setRenderer(
            renderer
        )

        # NoData остаётся прозрачным

        layer.triggerRepaint()

    # ---------------------------------------------------------
    # ЗАПУСК АНАЛИЗА
    # ---------------------------------------------------------

    def run_detection(self):

        before_layer = (
            self.before_combo
            .currentData()
        )

        after_layer = (
            self.after_combo
            .currentData()
        )

        band = (
            self.band_combo
            .currentData()
        )

        sigma = (
            self.sigma_spin.value()
        )

        min_region_size = (
            self.min_region_spin.value()
        )

        output_path = (
            self.output_edit
            .text()
            .strip()
        )

        # -----------------------------------------------------
        # Проверка выбора слоёв
        # -----------------------------------------------------

        if before_layer is None:

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не выбран снимок до."
            )

            return

        if after_layer is None:

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не выбран снимок после."
            )

            return

        if band is None:

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не выбран канал."
            )

            return

        if not output_path:

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не указан файл результата."
            )

            return

        # -----------------------------------------------------
        # Проверка совместимости растров
        # -----------------------------------------------------

        is_valid, message = (
            validate_rasters(
                before_layer,
                after_layer,
                band
            )
        )

        if not is_valid:

            QMessageBox.warning(
                self,
                "Растры несовместимы",
                message
            )

            return

        # -----------------------------------------------------
        # Запуск анализа
        # -----------------------------------------------------

        self.run_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Выполняется анализ...\n\n"
            "Для больших растров операция "
            "может занять некоторое время."
        )

        try:

            # -------------------------------------------------
            # Основной алгоритм
            # -------------------------------------------------

            result = detect_changes(
                before_layer,
                after_layer,
                band,
                sigma,
                min_region_size,
                output_path
            )

            # -------------------------------------------------
            # Открываем созданный GeoTIFF
            # -------------------------------------------------

            output_layer = (
                QgsRasterLayer(
                    output_path,
                    "Маска изменений"
                )
            )

            if not output_layer.isValid():

                raise ValueError(
                    "GeoTIFF был создан, "
                    "но QGIS не смог открыть "
                    "результат."
                )

            # -------------------------------------------------
            # Настраиваем отображение
            # -------------------------------------------------

            self.style_change_layer(
                output_layer
            )

            # -------------------------------------------------
            # Добавляем результат в проект
            # -------------------------------------------------

            QgsProject.instance().addMapLayer(
                output_layer
            )

            # -------------------------------------------------
            # Получаем статистику
            # -------------------------------------------------

            changed_before = (
                result[
                    "changed_before_filter"
                ]
            )

            changed_after = (
                result[
                    "changed_after_filter"
                ]
            )

            valid_pixels = (
                result[
                    "valid_pixels"
                ]
            )

            if valid_pixels > 0:

                change_percent = (
                    changed_after
                    / valid_pixels
                    * 100
                )

            else:

                change_percent = 0

            # -------------------------------------------------
            # Показываем результат
            # -------------------------------------------------

            self.status_label.setText(

                "Анализ завершён.\n\n"

                f"Общая сетка: "
                f"{result['width']} × "
                f"{result['height']}\n\n"

                f"Валидных пикселей: "
                f"{valid_pixels:,}\n"

                f"Среднее значение разности: "
                f"{result['mean']:.2f}\n"

                f"Стандартное отклонение: "
                f"{result['std']:.2f}\n"

                f"Порог: "
                f"{result['threshold']:.2f}\n\n"

                f"Изменений до фильтрации: "
                f"{changed_before:,}\n"

                f"Изменений после фильтрации: "
                f"{changed_after:,}\n"

                f"Доля изменений: "
                f"{change_percent:.2f}%\n\n"

                f"Результат:\n"
                f"{output_path}"
            )

            QMessageBox.information(
                self,
                "Анализ завершён",
                "Маска изменений успешно создана.\n\n"
                "Обнаруженные изменения "
                "отображаются красным цветом."
            )

        except Exception as error:

            self.status_label.setText(
                "Во время анализа "
                "произошла ошибка."
            )

            QMessageBox.critical(
                self,
                "Ошибка анализа",
                str(error)
            )

        finally:

            self.run_button.setEnabled(
                True
            )


     

