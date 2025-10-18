# coding: utf-8
import socket
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, pyqtSlot, Qt

try:
    from .logging_system import get_logger, LogCategory
except ImportError:
    from core.logging_system import get_logger, LogCategory  # type: ignore

logger = logging.getLogger(__name__)


class _CheckWorker(QObject):
    """Фоновый исполнитель проверки сетевого подключения."""
    result = pyqtSignal(bool)

    @pyqtSlot()
    def check(self) -> None:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.result.emit(True)
        except (socket.error, socket.timeout):
            self.result.emit(False)


class NetworkMonitor(QObject):
    """Монитор состояния подключения к интернету."""
    
    statusChanged = pyqtSignal(bool)  # True = подключено, False = отключено
    
    def __init__(self, check_interval_ms: int = 5000):
        super().__init__()
        self.net_logger = get_logger(LogCategory.NETWORK)
        self._is_connected = False
        self._check_interval = check_interval_ms
        self._timer = QTimer(self)
        # фоновой поток и воркер для неблокирующей проверки
        self._worker_thread = QThread(self)
        self._worker = _CheckWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker.result.connect(self._on_check_result)
        self._worker_thread.start()
        self._timer.timeout.connect(self._worker.check, type=Qt.QueuedConnection)
        
        self.net_logger.debug(f"Инициализация сетевого монитора (интервал: {check_interval_ms}ms)")
        
    def start(self):
        """Запустить мониторинг."""
        self.net_logger.info("Запуск мониторинга сетевого подключения")
        # первая проверка в фоне
        QTimer.singleShot(0, lambda: self._worker.check())
        self._timer.start(self._check_interval)
        
    def stop(self):
        """Остановить мониторинг."""
        self.net_logger.info("Остановка мониторинга сетевого подключения")
        self._timer.stop()
        try:
            self._worker_thread.quit()
            self._worker_thread.wait(1000)
        except Exception:
            pass
        
    def is_connected(self) -> bool:
        """Получить текущий статус подключения."""
        return self._is_connected
        
    @pyqtSlot(bool)
    def _on_check_result(self, new_status: bool) -> None:
        """Обработать результат фоновой проверки и оповестить при смене статуса."""
        if new_status == self._is_connected:
            return
        self._is_connected = new_status
        self.statusChanged.emit(self._is_connected)
        if self._is_connected:
            self.net_logger.info('Подключение к интернету восстановлено')
        else:
            self.net_logger.warning('Отсутствует подключение к интернету')
