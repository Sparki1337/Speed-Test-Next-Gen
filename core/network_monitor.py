# coding: utf-8
import socket
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

try:
    from .logging_system import get_logger, LogCategory
except ImportError:
    from core.logging_system import get_logger, LogCategory  # type: ignore

logger = logging.getLogger(__name__)


class NetworkMonitor(QObject):
    """Монитор состояния подключения к интернету."""
    
    statusChanged = pyqtSignal(bool)  # True = подключено, False = отключено
    
    def __init__(self, check_interval_ms: int = 5000):
        super().__init__()
        self.net_logger = get_logger(LogCategory.NETWORK)
        self._is_connected = False
        self._check_interval = check_interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_connection)
        
        self.net_logger.debug(f"Инициализация сетевого монитора (интервал: {check_interval_ms}ms)")
        
    def start(self):
        """Запустить мониторинг."""
        self.net_logger.info("Запуск мониторинга сетевого подключения")
        self._check_connection()  # Проверить сразу
        self._timer.start(self._check_interval)
        
    def stop(self):
        """Остановить мониторинг."""
        self.net_logger.info("Остановка мониторинга сетевого подключения")
        self._timer.stop()
        
    def is_connected(self) -> bool:
        """Получить текущий статус подключения."""
        return self._is_connected
        
    def _check_connection(self):
        """Проверить подключение к интернету."""
        try:
            # Пробуем подключиться к DNS серверам Google
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            new_status = True
        except (socket.error, socket.timeout):
            new_status = False
        
        # Отправляем сигнал только если статус изменился
        if new_status != self._is_connected:
            self._is_connected = new_status
            self.statusChanged.emit(self._is_connected)
            if self._is_connected:
                self.net_logger.info('Подключение к интернету восстановлено')
                logger.info('Подключение к интернету восстановлено')
            else:
                self.net_logger.warning('Отсутствует подключение к интернету')
                logger.warning('Отсутствует подключение к интернету')
