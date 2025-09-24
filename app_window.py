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
    from fluent_speedtest.utils import import_attrs
except ImportError:  # запуск из каталога
    from utils import import_attrs  # type: ignore

TestInterface, = import_attrs("ui.test_interface", "TestInterface")
HistoryInterface, = import_attrs("ui.history_interface", "HistoryInterface")
SettingsInterface, = import_attrs("ui.settings_interface", "SettingsInterface")
ServersInterface, = import_attrs("ui.servers_interface", "ServersInterface")


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
        self.setWindowTitle('Speedtest NextGen by Sparki | v1.1.2 Beta')

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
