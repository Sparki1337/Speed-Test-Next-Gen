# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QLabel, QHBoxLayout, QWidget

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
    from .core.network_monitor import NetworkMonitor
    from .version import get_window_title
except ImportError:
    # Запуск без пакета (python app_window.py / python main.py в каталоге)
    from ui.test_interface import TestInterface  # type: ignore
    from ui.history_interface import HistoryInterface  # type: ignore
    from ui.settings_interface import SettingsInterface  # type: ignore
    from ui.servers_interface import ServersInterface  # type: ignore
    from core.network_monitor import NetworkMonitor  # type: ignore
    from version import get_window_title  # type: ignore


class AppWindow(FluentWindow):
    def __init__(self, emitter=None):
        super().__init__()
        self.emitter = emitter

        self.testInterface = TestInterface(emitter=self.emitter, parent=self)
        self.serversInterface = ServersInterface(parent=self)
        self.historyInterface = HistoryInterface(parent=self)
        self.settingsInterface = SettingsInterface(parent=self)

        # Монитор подключения к интернету
        self.networkMonitor = NetworkMonitor(check_interval_ms=5000)
        self.networkMonitor.statusChanged.connect(self._on_network_status_changed)

        self.initNavigation()
        self.initWindow()
        self.initNetworkIndicator()
        
        # Запустить мониторинг сети
        self.networkMonitor.start()

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
        self.setWindowTitle(get_window_title())

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def initNetworkIndicator(self):
        """Инициализировать индикатор статуса интернета в заголовке окна."""
        # Создаём виджет для индикатора
        self.networkIndicatorWidget = QWidget(self)
        self.networkIndicatorLayout = QHBoxLayout(self.networkIndicatorWidget)
        self.networkIndicatorLayout.setContentsMargins(0, 0, 10, 0)
        self.networkIndicatorLayout.setSpacing(5)
        
        # Иконка статуса (кружок)
        self.networkStatusIcon = QLabel('●', self.networkIndicatorWidget)
        self.networkStatusIcon.setStyleSheet('font-size: 14px; color: #10893E;')
        
        # Текст статуса
        self.networkStatusLabel = QLabel('Подключено', self.networkIndicatorWidget)
        self.networkStatusLabel.setStyleSheet('font-size: 12px; color: rgba(255, 255, 255, 0.8);')
        
        self.networkIndicatorLayout.addWidget(self.networkStatusIcon)
        self.networkIndicatorLayout.addWidget(self.networkStatusLabel)
        
        # Добавляем индикатор в titleBar (если доступен)
        try:
            self.titleBar.hBoxLayout.insertWidget(0, self.networkIndicatorWidget)
        except Exception:
            # Если не удалось добавить в titleBar, просто скрываем
            self.networkIndicatorWidget.hide()

    def _on_network_status_changed(self, is_connected: bool):
        """Обработчик изменения статуса подключения к интернету."""
        if is_connected:
            self.networkStatusIcon.setStyleSheet('font-size: 14px; color: #10893E;')  # Зелёный
            self.networkStatusLabel.setText('Подключено')
        else:
            self.networkStatusIcon.setStyleSheet('font-size: 14px; color: #E81123;')  # Красный
            self.networkStatusLabel.setText('Нет подключения')

    def closeEvent(self, event):
        """Остановить мониторинг сети при закрытии окна."""
        self.networkMonitor.stop()
        super().closeEvent(event)
