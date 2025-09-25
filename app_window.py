# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    FluentIcon as FIF,
)

try:
    from .ui.test_interface import TestInterface
    from .ui.history_interface import HistoryInterface
    from .ui.settings_interface import SettingsInterface
    from .ui.servers_interface import ServersInterface
except ImportError:
    # Запуск без пакета (python app_window.py / python main.py в каталоге)
    from ui.test_interface import TestInterface  # type: ignore
    from ui.history_interface import HistoryInterface  # type: ignore
    from ui.settings_interface import SettingsInterface  # type: ignore
    from ui.servers_interface import ServersInterface  # type: ignore


class AppWindow(FluentWindow):
    def __init__(self, emitter=None):
        super().__init__()
        self.emitter = emitter

        self.testInterface = TestInterface(emitter=self.emitter, parent=self)
        self.serversInterface = ServersInterface(parent=self)
        self.historyInterface = HistoryInterface(parent=self)
        self.settingsInterface = SettingsInterface(parent=self)

        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        # Основные разделы
        self.addSubInterface(self.testInterface, FIF.SPEED_HIGH, 'Тест скорости')
        self.addSubInterface(self.serversInterface, FIF.WIFI, 'Серверы')
        self.addSubInterface(self.historyInterface, FIF.HISTORY, 'История')

        # Нижняя часть (настройки)
        self.addSubInterface(self.settingsInterface, FIF.SETTING, 'Настройки', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(980, 700)
        self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        self.setWindowTitle('Speedtest NextGen by Sparki | v1.2.1 | Release')

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
