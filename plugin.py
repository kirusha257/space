from qgis.PyQt.QtWidgets import QAction

from .gui.dialog import ChangeDetectorDialog


class ChangeDetectorPlugin:

    def __init__(self, iface):

        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):

        self.action = QAction(
            "Детектор изменений растров",
            self.iface.mainWindow()
        )

        self.action.triggered.connect(
            self.run
        )

        self.iface.addPluginToMenu(
            "&Raster Change Detector",
            self.action
        )

        self.iface.addToolBarIcon(
            self.action
        )

    def unload(self):

        if self.action:

            self.iface.removePluginMenu(
                "&Raster Change Detector",
                self.action
            )

            self.iface.removeToolBarIcon(
                self.action
            )

    def run(self):

        self.dialog = ChangeDetectorDialog(
            self.iface,
            self.iface.mainWindow()
        )

        self.dialog.show()