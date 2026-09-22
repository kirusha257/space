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
    QFileDialog,
    QCheckBox
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

        self.setMinimumWidth(560)

        self.create_ui()

        self.load_raster_layers()

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def create_ui(self):

        main_layout = QVBoxLayout()

        # =====================================================
        # ИСХОДНЫЕ РАСТРЫ
        # =====================================================

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

        # =====================================================
        # QA_PIXEL
        # =====================================================

        qa_group = QGroupBox(
            "Маскирование облаков"
        )

        qa_layout = QFormLayout()

        self.use_qa_checkbox = QCheckBox(
            "Использовать QA_PIXEL"
        )

        self.use_qa_checkbox.setChecked(
            True
        )

        qa_layout.addRow(
            self.use_qa_checkbox
        )

        self.before_qa_combo = QComboBox()
        self.after_qa_combo = QComboBox()

        qa_layout.addRow(
            "QA до:",
            self.before_qa_combo
        )

        qa_layout.addRow(
            "QA после:",
            self.after_qa_combo
        )

        qa_group.setLayout(
            qa_layout
        )

        main_layout.addWidget(
            qa_group
        )

        # =====================================================
        # ПАРАМЕТРЫ АНАЛИЗА
        # =====================================================

        parameter_group = QGroupBox(
            "Параметры анализа"
        )

        parameter_layout = QFormLayout()

        # -----------------------------------------------------
        # Канал
        # -----------------------------------------------------

        self.band_combo = QComboBox()

        parameter_layout.addRow(
            "Канал:",
            self.band_combo
        )

        # -----------------------------------------------------
        # Sigma
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Минимальный размер области
        # -----------------------------------------------------

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

        # =====================================================
        # РЕЗУЛЬТАТ
        # =====================================================

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

        # =====================================================
        # КНОПКА ЗАПУСКА
        # =====================================================

        self.run_button = QPushButton(
            "Определить изменения"
        )

        self.run_button.clicked.connect(
            self.run_detection
        )

        main_layout.addWidget(
            self.run_button
        )

        # =====================================================
        # СТАТУС
        # =====================================================

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

        # =====================================================
        # СИГНАЛЫ
        # =====================================================

        self.before_combo.currentIndexChanged.connect(
            self.update_bands
        )

        self.use_qa_checkbox.stateChanged.connect(
            self.update_qa_controls
        )

    # =========================================================
    # ЗАГРУЗКА РАСТРОВЫХ СЛОЁВ
    # =========================================================

    def load_raster_layers(self):

        self.before_combo.clear()
        self.after_combo.clear()

        self.before_qa_combo.clear()
        self.after_qa_combo.clear()

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

        # -----------------------------------------------------
        # Основные растры
        # -----------------------------------------------------

        for layer in raster_layers:

            self.before_combo.addItem(
                layer.name(),
                layer
            )

            self.after_combo.addItem(
                layer.name(),
                layer
            )

        # -----------------------------------------------------
        # QA-растры
        # -----------------------------------------------------

        for layer in raster_layers:

            layer_name = (
                layer.name()
                .upper()
            )

            if (
                "QA_PIXEL" in layer_name
                or "QA_PIXEL" in layer.source().upper()
            ):

                self.before_qa_combo.addItem(
                    layer.name(),
                    layer
                )

                self.after_qa_combo.addItem(
                    layer.name(),
                    layer
                )

        # -----------------------------------------------------
        # Пытаемся автоматически выбрать QA
        # -----------------------------------------------------

        self.auto_select_qa_layers()

        self.update_bands()

        self.update_qa_controls()

    # =========================================================
    # АВТОМАТИЧЕСКИЙ ВЫБОР QA
    # =========================================================

    def auto_select_qa_layers(self):

        qa_count = (
            self.before_qa_combo.count()
        )

        if qa_count == 0:
            return

        before_name = (
            self.before_combo
            .currentText()
            .lower()
        )

        after_name = (
            self.after_combo
            .currentText()
            .lower()
        )

        # -----------------------------------------------------
        # Ищем QA с похожим названием
        # -----------------------------------------------------

        for index in range(
            qa_count
        ):

            qa_name = (
                self.before_qa_combo
                .itemText(index)
                .lower()
            )

            if (
                before_name
                and before_name.split("_")[0]
                in qa_name
            ):

                self.before_qa_combo.setCurrentIndex(
                    index
                )

                break

        for index in range(
            self.after_qa_combo.count()
        ):

            qa_name = (
                self.after_qa_combo
                .itemText(index)
                .lower()
            )

            if (
                after_name
                and after_name.split("_")[0]
                in qa_name
            ):

                self.after_qa_combo.setCurrentIndex(
                    index
                )

                break

    # =========================================================
    # УПРАВЛЕНИЕ QA
    # =========================================================

    def update_qa_controls(self):

        enabled = (
            self.use_qa_checkbox.isChecked()
        )

        self.before_qa_combo.setEnabled(
            enabled
        )

        self.after_qa_combo.setEnabled(
            enabled
        )

    # =========================================================
    # ОБНОВЛЕНИЕ КАНАЛОВ
    # =========================================================

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

    # =========================================================
    # ВЫБОР ФАЙЛА
    # =========================================================

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

    # =========================================================
    # ОТОБРАЖЕНИЕ МАСКИ
    # =========================================================

    def style_change_layer(
        self,
        layer
    ):

        color_ramp = (
            QgsColorRampShader()
        )

        color_ramp.setColorRampType(
            QgsColorRampShader.Discrete
        )

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

        raster_shader = (
            QgsRasterShader()
        )

        raster_shader.setRasterShaderFunction(
            color_ramp
        )

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

        layer.triggerRepaint()

    # =========================================================
    # ЗАПУСК АНАЛИЗА
    # =========================================================

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

        use_qa = (
            self.use_qa_checkbox
            .isChecked()
        )

        before_qa_layer = (
            self.before_qa_combo
            .currentData()
            if use_qa
            else None
        )

        after_qa_layer = (
            self.after_qa_combo
            .currentData()
            if use_qa
            else None
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
        # Проверка выбора
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
        # Проверка QA
        # -----------------------------------------------------

        if use_qa:

            if before_qa_layer is None:

                QMessageBox.warning(
                    self,
                    "Ошибка QA",
                    "Не выбран QA_PIXEL "
                    "для снимка до."
                )

                return

            if after_qa_layer is None:

                QMessageBox.warning(
                    self,
                    "Ошибка QA",
                    "Не выбран QA_PIXEL "
                    "для снимка после."
                )

                return

        # -----------------------------------------------------
        # Проверка основных растров
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
        # Запуск
        # -----------------------------------------------------

        self.run_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Выполняется анализ...\n\n"
            "Подготавливаются данные "
            "и маска QA_PIXEL."
        )

        try:

            result = detect_changes(
                before_layer,
                after_layer,
                band,
                sigma,
                min_region_size,
                output_path,
                before_qa_layer,
                after_qa_layer
            )

            # -------------------------------------------------
            # Открываем результат
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

            self.style_change_layer(
                output_layer
            )

            QgsProject.instance().addMapLayer(
                output_layer
            )

            # -------------------------------------------------
            # Статистика
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

            masked_pixels = (
                result[
                    "qa_masked_pixels"
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
            # Результат
            # -------------------------------------------------

            self.status_label.setText(

                "Анализ завершён.\n\n"

                f"Общая сетка: "
                f"{result['width']} × "
                f"{result['height']}\n\n"

                f"Валидных пикселей: "
                f"{valid_pixels:,}\n"

                f"Замаскировано QA_PIXEL: "
                f"{masked_pixels:,}\n\n"

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
                "Облака, облачные тени, cirrus "
                "и снег исключены из анализа "
                "по QA_PIXEL."
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