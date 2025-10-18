# coding: utf-8
"""
Профессиональная система логирования для Fluent Speedtest.

Возможности:
- Категории логирования (APP, UI, TEST, NETWORK, SETTINGS, HISTORY, ERROR)
- Множество форматов (JSON для файлов, человекочитаемый для UI/консоли)
- Ротация логов (по времени и размеру)
- Асинхронная запись в файлы (не блокирует GUI)
- Буферизация записей (опционально)
- Гибкая настройка уровней логирования
- Поддержка структурированных данных
"""
import json
import logging
import os
import sys
import threading
from datetime import datetime, timedelta
from enum import Enum
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Dict, Optional


class LogCategory(str, Enum):
    """Категории событий для логирования."""
    APP = "APP"           # Приложение: запуск, закрытие, инициализация
    UI = "UI"             # UI: открытие окон, вкладок, клики кнопок
    TEST = "TEST"         # Тесты: начало, прогресс, завершение, отмена
    NETWORK = "NETWORK"   # Сеть: изменения подключения, выбор серверов
    SETTINGS = "SETTINGS" # Настройки: изменения параметров
    HISTORY = "HISTORY"   # История: экспорт, очистка, загрузка
    ERROR = "ERROR"       # Ошибки: детальные трассировки


class JSONFormatter(logging.Formatter):
    """Форматтер для записи логов в JSON формате."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'category': getattr(record, 'category', 'APP'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Добавить extra данные если есть
        if hasattr(record, 'extra_data') and record.extra_data:
            log_data['data'] = record.extra_data
        
        # Добавить информацию об исключении если есть
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Форматтер для человекочитаемого вывода в UI и консоль."""
    
    def __init__(self, show_category: bool = True, colored: bool = False):
        self.show_category = show_category
        self.colored = colored
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        level = record.levelname
        category = getattr(record, 'category', 'APP')
        message = record.getMessage()
        
        if self.show_category:
            log_line = f"{timestamp} {level:8} {category:8} {message}"
        else:
            log_line = f"{timestamp} {level:8} {message}"
        
        # Добавить трассировку исключения если есть
        if record.exc_info:
            log_line += '\n' + self.formatException(record.exc_info)
        
        return log_line


class AsyncFileHandler(logging.Handler):
    """
    Асинхронный обработчик для записи логов в файл.
    Записи помещаются в очередь и обрабатываются в отдельном потоке.
    """
    
    def __init__(self, filepath: str, formatter: logging.Formatter, 
                 buffer_size: int = 0, flush_interval: float = 1.0):
        """
        Args:
            filepath: Путь к файлу логов
            formatter: Форматтер для записей
            buffer_size: Размер буфера (0 = без буферизации)
            flush_interval: Интервал принудительной записи буфера (секунды)
        """
        super().__init__()
        self.filepath = Path(filepath)
        self.setFormatter(formatter)
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Создать директорию если не существует
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Очередь для асинхронной записи
        self.queue: Queue = Queue()
        self.buffer: list = []
        self.last_flush_time = datetime.now()
        
        # Флаг остановки и поток записи
        self._stop_event = threading.Event()
        self._writer_thread = threading.Thread(
            target=self._write_loop,
            name='LogWriter',
            daemon=True
        )
        self._writer_thread.start()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Добавить запись в очередь для асинхронной записи."""
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)
    
    def _write_loop(self) -> None:
        """Основной цикл записи в файл (выполняется в отдельном потоке)."""
        while not self._stop_event.is_set():
            try:
                # Получить запись из очереди (таймаут для проверки _stop_event)
                try:
                    msg = self.queue.get(timeout=0.1)
                except Empty:
                    # Проверить буфер на необходимость сброса по таймауту
                    if self.buffer and (datetime.now() - self.last_flush_time).total_seconds() >= self.flush_interval:
                        self._flush_buffer()
                    continue
                
                if self.buffer_size > 0:
                    # Буферизованная запись
                    self.buffer.append(msg)
                    if len(self.buffer) >= self.buffer_size:
                        self._flush_buffer()
                else:
                    # Прямая запись без буферизации
                    with open(self.filepath, 'a', encoding='utf-8') as f:
                        f.write(msg + '\n')
            
            except Exception as e:
                # Логирование ошибок записи в stderr
                print(f"[AsyncFileHandler] Ошибка записи: {e}", file=sys.stderr)
        
        # Сбросить оставшиеся записи при остановке
        self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Сбросить буфер в файл."""
        if not self.buffer:
            return
        
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                for msg in self.buffer:
                    f.write(msg + '\n')
            self.buffer.clear()
            self.last_flush_time = datetime.now()
        except Exception as e:
            print(f"[AsyncFileHandler] Ошибка сброса буфера: {e}", file=sys.stderr)
    
    def close(self) -> None:
        """Остановить поток записи и закрыть обработчик."""
        self._stop_event.set()
        if self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5.0)
        super().close()


class RotatingLogManager:
    """
    Менеджер для ротации логов по времени.
    Удаляет старые файлы логов (старше N дней).
    """
    
    def __init__(self, log_dir: Path, max_days: int = 7):
        """
        Args:
            log_dir: Директория с логами
            max_days: Максимальное количество дней хранения логов
        """
        self.log_dir = log_dir
        self.max_days = max_days
    
    def cleanup_old_logs(self) -> None:
        """Удалить старые файлы логов."""
        if not self.log_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.max_days)
        
        for log_file in self.log_dir.glob('*.log'):
            try:
                # Проверить время модификации файла
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_date:
                    log_file.unlink()
                    print(f"[RotatingLogManager] Удалён старый лог: {log_file.name}")
            except Exception as e:
                print(f"[RotatingLogManager] Ошибка удаления {log_file.name}: {e}", file=sys.stderr)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Адаптер для логгера с поддержкой категорий и структурированных данных.
    """
    
    def __init__(self, logger: logging.Logger, category: LogCategory):
        super().__init__(logger, {})
        self.category = category
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Добавить категорию и extra данные к записи."""
        # Получить extra данные из kwargs
        extra = kwargs.get('extra', {})
        extra['category'] = self.category.value
        
        # Если переданы структурированные данные, добавить их
        if 'data' in kwargs:
            extra['extra_data'] = kwargs.pop('data')
        
        kwargs['extra'] = extra
        return msg, kwargs


class LoggingSystem:
    """
    Центральная система логирования приложения.
    Управляет всеми обработчиками, форматтерами и настройками логирования.
    """
    
    def __init__(self):
        self.root_logger = logging.getLogger()
        self.handlers: Dict[str, logging.Handler] = {}
        self.loggers: Dict[LogCategory, LoggerAdapter] = {}
        self._initialized = False
    
    def initialize(
        self,
        log_dir: Optional[str] = None,
        log_level: int = logging.INFO,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_ui: bool = False,
        ui_emitter=None,
        buffer_size: int = 0,
        max_log_days: int = 7
    ) -> None:
        """
        Инициализировать систему логирования.
        
        Args:
            log_dir: Директория для файлов логов (по умолчанию: Documents/SpeedtestNextGen/logs)
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_console: Включить вывод в консоль
            enable_file: Включить запись в файлы
            enable_ui: Включить вывод в UI
            ui_emitter: Эмиттер для отправки логов в UI (LogEmitter)
            buffer_size: Размер буфера для файловой записи (0 = без буферизации)
            max_log_days: Количество дней хранения логов
        """
        if self._initialized:
            return
        
        # Очистить существующие обработчики
        self.root_logger.handlers.clear()
        self.root_logger.setLevel(log_level)
        
        # Определить директорию логов
        if log_dir is None:
            log_dir = self._get_default_log_dir()
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Ротация логов: удалить старые файлы
        if enable_file and max_log_days > 0:
            rotation_manager = RotatingLogManager(log_path, max_log_days)
            rotation_manager.cleanup_old_logs()
        
        # Консольный обработчик (человекочитаемый формат)
        if enable_console and self._console_available():
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(HumanReadableFormatter(show_category=True))
            self.root_logger.addHandler(console_handler)
            self.handlers['console'] = console_handler
        
        # Файловый обработчик (JSON формат)
        if enable_file:
            log_filename = datetime.now().strftime('speedtest_%Y%m%d_%H%M%S.log')
            log_filepath = log_path / log_filename
            
            file_handler = AsyncFileHandler(
                filepath=str(log_filepath),
                formatter=JSONFormatter(),
                buffer_size=buffer_size,
                flush_interval=1.0
            )
            file_handler.setLevel(log_level)
            self.root_logger.addHandler(file_handler)
            self.handlers['file'] = file_handler
        
        # UI обработчик (человекочитаемый формат)
        if enable_ui and ui_emitter is not None:
            try:
                from ..logging_utils import UILogHandler  # при импорте как пакет
            except Exception:  # fallback при локальном запуске из каталога
                from logging_utils import UILogHandler  # type: ignore
            ui_handler = UILogHandler(ui_emitter)
            ui_handler.setLevel(log_level)
            ui_handler.setFormatter(HumanReadableFormatter(show_category=True))
            self.root_logger.addHandler(ui_handler)
            self.handlers['ui'] = ui_handler
        
        # Создать адаптеры для каждой категории
        for category in LogCategory:
            self.loggers[category] = LoggerAdapter(self.root_logger, category)
        
        self._initialized = True
        
        # Записать стартовое сообщение
        self.get_logger(LogCategory.APP).info(
            "Система логирования инициализирована",
            data={
                'log_dir': str(log_path),
                'log_level': logging.getLevelName(log_level),
                'console': enable_console,
                'file': enable_file,
                'ui': enable_ui,
                'buffer_size': buffer_size
            }
        )
    
    def get_logger(self, category: LogCategory = LogCategory.APP) -> LoggerAdapter:
        """
        Получить логгер для определённой категории.
        
        Args:
            category: Категория событий
        
        Returns:
            LoggerAdapter для указанной категории
        """
        if not self._initialized:
            # Если не инициализировано, инициализировать с настройками по умолчанию
            self.initialize()
        
        return self.loggers.get(category, self.loggers[LogCategory.APP])
    
    def set_level(self, level: int) -> None:
        """
        Изменить уровень логирования для всех обработчиков.
        
        Args:
            level: Новый уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.root_logger.setLevel(level)
        for handler in self.root_logger.handlers:
            handler.setLevel(level)
        
        self.get_logger(LogCategory.APP).info(
            f"Уровень логирования изменён на {logging.getLevelName(level)}"
        )
    
    def set_buffer_size(self, buffer_size: int) -> None:
        """
        Изменить размер буфера для файлового обработчика.
        
        Args:
            buffer_size: Новый размер буфера (0 = без буферизации)
        """
        if 'file' in self.handlers:
            handler = self.handlers['file']
            if isinstance(handler, AsyncFileHandler):
                handler.buffer_size = buffer_size
                self.get_logger(LogCategory.APP).info(
                    f"Размер буфера логов изменён на {buffer_size}"
                )
    
    def shutdown(self) -> None:
        """Корректно завершить работу системы логирования."""
        if not self._initialized:
            return
        
        self.get_logger(LogCategory.APP).info("Завершение работы системы логирования")
        
        # Закрыть все обработчики
        for handler in list(self.root_logger.handlers):
            try:
                handler.close()
                self.root_logger.removeHandler(handler)
            except Exception as e:
                print(f"[LoggingSystem] Ошибка закрытия обработчика: {e}", file=sys.stderr)
        
        self.handlers.clear()
        self.loggers.clear()
        self._initialized = False
    
    @staticmethod
    def _get_default_log_dir() -> str:
        """Получить путь к директории логов по умолчанию."""
        if sys.platform == 'win32':
            docs_path = Path(os.path.expanduser('~')) / 'Documents' / 'SpeedtestNextGen' / 'logs'
        else:
            docs_path = Path.home() / '.speedtest' / 'logs'
        return str(docs_path)
    
    @staticmethod
    def _console_available() -> bool:
        """Проверить, доступна ли консоль для вывода."""
        try:
            if sys.stdout is None:
                return False
            is_tty = getattr(sys.stdout, "isatty", lambda: False)()
            return bool(is_tty)
        except Exception:
            return False


# Глобальный экземпляр системы логирования
_logging_system: Optional[LoggingSystem] = None


def get_logging_system() -> LoggingSystem:
    """Получить глобальный экземпляр системы логирования (Singleton)."""
    global _logging_system
    if _logging_system is None:
        _logging_system = LoggingSystem()
    return _logging_system


def get_logger(category: LogCategory = LogCategory.APP) -> LoggerAdapter:
    """
    Удобная функция для получения логгера.
    
    Args:
        category: Категория событий
    
    Returns:
        LoggerAdapter для указанной категории
    
    Example:
        >>> from core.logging_system import get_logger, LogCategory
        >>> logger = get_logger(LogCategory.UI)
        >>> logger.info("Открыто главное окно", data={'window': 'MainWindow'})
    """
    return get_logging_system().get_logger(category)
