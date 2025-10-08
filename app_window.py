# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QHBoxLayout,
    QWidget,
    QSystemTrayIcon,
    QMenu,
    QAction,
)

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
    from .core.logging_system import get_logger, LogCategory
    from .version import get_window_title
except ImportError:
    # Запуск без пакета (python app_window.py / python main.py в каталоге)
    from ui.test_interface import TestInterface  # type: ignore
    from ui.history_interface import HistoryInterface  # type: ignore
    from ui.settings_interface import SettingsInterface  # type: ignore
    from ui.servers_interface import ServersInterface  # type: ignore
    from core.network_monitor import NetworkMonitor  # type: ignore
    from core.logging_system import get_logger, LogCategory  # type: ignore
    from version import get_window_title  # type: ignore


class AppWindow(FluentWindow):
    def __init__(self, emitter=None):
        super().__init__()
        self.logger = get_logger(LogCategory.UI)
        self.emitter = emitter
        self._is_exiting = False
        self._tray_tip_shown = False
        
        self.logger.info("Инициализация главного окна приложения")

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
        self.initTray()
        
        # Запустить мониторинг сети
        self.networkMonitor.start()

    def initNavigation(self):
        self.logger.debug("Инициализация навигации")
        
        # Основные разделы
        self.addSubInterface(self.testInterface, FIF.SPEED_HIGH, 'Тест скорости')
        self.addSubInterface(self.serversInterface, FIF.WIFI, 'Серверы')
        self.addSubInterface(self.historyInterface, FIF.HISTORY, 'История')

        # Нижняя часть (настройки)
        self.addSubInterface(self.settingsInterface, FIF.SETTING, 'Настройки', NavigationItemPosition.BOTTOM)
        
        # Подключение обработчика переключения вкладок
        self.stackedWidget.currentChanged.connect(self._on_tab_changed)
        
        self.logger.info("Навигация инициализирована: 4 вкладки")

    def initWindow(self):
        self.logger.debug("Настройка параметров окна")
        
        self.resize(980, 700)
        self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        self.setWindowTitle(get_window_title())

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        
        self.logger.info("Окно настроено", data={
            'width': 980,
            'height': 700,
            'title': get_window_title()
        })

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

    def initTray(self):
        """Инициализация иконки в трее и контекстного меню."""
        try:
            icon = QIcon(':/qfluentwidgets/images/logo.png')
        except Exception:
            icon = self.windowIcon()

        self.trayIcon = QSystemTrayIcon(icon, self)

        menu = QMenu(self)

        actionOpen = QAction("Открыть", self)
        actionOpen.triggered.connect(self.show_main_window)

        actionStart = QAction("Начать тест", self)
        actionStart.triggered.connect(self._start_test_from_tray)

        menu.addAction(actionOpen)
        menu.addAction(actionStart)
        menu.addSeparator()

        actionQuit = QAction("Выход", self)
        actionQuit.triggered.connect(self._quit_from_tray)
        menu.addAction(actionQuit)

        self.trayIcon.setContextMenu(menu)
        self.trayIcon.activated.connect(self._on_tray_activated)
        self.trayIcon.setToolTip(self.windowTitle())
        self.trayIcon.show()

    # --- ТРЕЙ: обработчики ---
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_main_window()

    def show_main_window(self):
        """Показать главное окно и вывести на передний план."""
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def _start_test_from_tray(self):
        """Запуск обычного теста из трея."""
        try:
            self.show_main_window()
            self.stackedWidget.setCurrentWidget(self.testInterface)
            self.testInterface.start_test()
        except Exception as e:
            self.logger.error(f"Не удалось запустить тест из трея: {e}")

    def _quit_from_tray(self):
        """Полное завершение приложения из трея."""
        self._is_exiting = True
        try:
            self.trayIcon.hide()
        except Exception:
            pass
        QApplication.instance().quit()

    def _on_network_status_changed(self, is_connected: bool):
        """Обработчик изменения статуса подключения к интернету."""
        if is_connected:
            self.networkStatusIcon.setStyleSheet('font-size: 14px; color: #10893E;')  # Зелёный
            self.networkStatusLabel.setText('Подключено')
        else:
            self.networkStatusIcon.setStyleSheet('font-size: 14px; color: #E81123;')  # Красный
            self.networkStatusLabel.setText('Нет подключения')

    def _on_tab_changed(self, index: int):
        """Обработчик переключения вкладок."""
        current_widget = self.stackedWidget.widget(index)
        
        # Определить имя вкладки
        tab_name = "Неизвестно"
        if current_widget == self.testInterface:
            tab_name = "Тест скорости"
        elif current_widget == self.serversInterface:
            tab_name = "Серверы"
        elif current_widget == self.historyInterface:
            tab_name = "История"
        elif current_widget == self.settingsInterface:
            tab_name = "Настройки"
        
        self.logger.info(f"Переключение на вкладку: {tab_name}", data={
            'tab_name': tab_name,
            'tab_index': index
        })
        
        # Обновляем историю при переходе на вкладку истории
        if current_widget == self.historyInterface:
            self.historyInterface.refresh()

    def closeEvent(self, event):
        """Сворачиваем в трей вместо выхода; выход через пункт "Выход"."""
        if self._is_exiting:
            self.logger.info("Закрытие приложения по запросу пользователя (трей)")
            try:
                self.trayIcon.hide()
            except Exception:
                pass
            self.networkMonitor.stop()
            super().closeEvent(event)
            return

        event.ignore()
        self.hide()
        self.logger.info("Окно скрыто в трей")
        # Показать подсказку один раз
        if not self._tray_tip_shown and hasattr(self, 'trayIcon') and self.trayIcon.isVisible():
            try:
                self.trayIcon.showMessage(
                    "Fluent Speedtest",
                    "Приложение продолжает работать в трее. Кликните, чтобы открыть.",
                    QSystemTrayIcon.Information,
                    3000,
                )
                self._tray_tip_shown = True
            except Exception:
                pass
