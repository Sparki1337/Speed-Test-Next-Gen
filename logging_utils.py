# coding: utf-8
"""
Утилиты логирования для Fluent Speedtest.
Обеспечивает совместимость со старым кодом и интеграцию с новой системой логирования.
"""
import logging
from PyQt5.QtCore import QObject, pyqtSignal

try:
    from .core.logging_system import get_logging_system, LogCategory
except ImportError:
    from core.logging_system import get_logging_system, LogCategory  # type: ignore


class LogEmitter(QObject):
    """Эмиттер для отправки сообщений логов в UI через Qt сигналы."""
    message = pyqtSignal(str)


class UILogHandler(logging.Handler):
    """Обработчик для вывода логов в UI компонент."""
    
    def __init__(self, emitter: LogEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.emitter.message.emit(msg)


def setup_logging(ui_emitter: LogEmitter = None, level: int = logging.INFO, enabled: bool = True):
    """
    Инициализировать систему логирования (обратная совместимость со старым кодом).
    
    Args:
        ui_emitter: Эмиттер для отправки логов в UI
        level: Уровень логирования
        enabled: Включить логирование
    
    Returns:
        Root logger
    """
    logging_system = get_logging_system()
    
    # Получить настройки буферизации из настроек приложения
    buffer_size = 0
    try:
        from core.settings import get_settings
        settings = get_settings()
        buffer_size = int(settings.get('log_buffer_size', 0))
    except Exception:
        pass
    
    if enabled:
        logging_system.initialize(
            log_level=level,
            enable_console=True,
            enable_file=True,
            enable_ui=bool(ui_emitter),
            ui_emitter=ui_emitter,
            buffer_size=buffer_size,
            max_log_days=7
        )
    
    return logging.getLogger()


def apply_logging_enabled(enabled: bool, ui_emitter: LogEmitter = None, level: int = logging.INFO):
    """
    Динамически применить включение/выключение логов (обратная совместимость).
    
    Args:
        enabled: Включить логирование
        ui_emitter: Эмиттер для отправки логов в UI
        level: Уровень логирования
    """
    if enabled:
        setup_logging(ui_emitter=ui_emitter, level=level, enabled=True)
    else:
        # Выключить логирование
        logging_system = get_logging_system()
        logging_system.shutdown()