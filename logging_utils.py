# coding: utf-8
import logging
import sys
from PyQt5.QtCore import QObject, pyqtSignal


class LogEmitter(QObject):
    message = pyqtSignal(str)


class UILogHandler(logging.Handler):
    def __init__(self, emitter: LogEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.emitter.message.emit(msg)

def _console_available() -> bool:
    # Проверить, есть ли доступный stdout (консоль/терминал).
    # В GUI-сборках (Nuitka --windows-console-mode=disable) stdout обычно отсутствует
    # или не является TTY, и попытки записи могут блокировать/вызывать ошибки.
    try:
        if sys.stdout is None:
            return False
        is_tty = getattr(sys.stdout, "isatty", lambda: False)()
        # Иногда isatty() False, но писать можно — в таком случае не добавляем StreamHandler,
        # так как пользы мало. Возвращаем строго только TTY.
        return bool(is_tty)
    except Exception:
        return False

def setup_logging(ui_emitter: LogEmitter = None, level=logging.INFO, enabled: bool = True):
    # Инициализировать логирование. Если enabled=False — обработчики не добавляются.
    logger = logging.getLogger()
    logger.setLevel(level)

    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')

    if not enabled:
        # удалить все наши обработчики, если они есть
        for h in list(logger.handlers):
            if isinstance(h, (logging.StreamHandler, UILogHandler)):
                logger.removeHandler(h)
        return logger

    # не дублировать обработчики
    if _console_available() and not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        try:
            ch = logging.StreamHandler(stream=sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(fmt)
            logger.addHandler(ch)
        except Exception:
            # В GUI-режиме безопасно игнорируем невозможность добавить StreamHandler
            pass

    if ui_emitter and not any(isinstance(h, UILogHandler) for h in logger.handlers):
        uh = UILogHandler(ui_emitter)
        uh.setLevel(level)
        uh.setFormatter(fmt)
        logger.addHandler(uh)

    return logger


def apply_logging_enabled(enabled: bool, ui_emitter: LogEmitter = None, level=logging.INFO):
    # Динамически применить включение/выключение логов.
    # Если enabled=True, убедиться, что StreamHandler и UILogHandler присутствуют
    # Если enabled=False, удалить StreamHandler и UILogHandler
 
    logger = logging.getLogger()
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')

    if not enabled:
        for h in list(logger.handlers):
            if isinstance(h, (logging.StreamHandler, UILogHandler)):
                logger.removeHandler(h)
        return

    # включить True -> ensure handlers
    if _console_available() and not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        try:
            ch = logging.StreamHandler(stream=sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(fmt)
            logger.addHandler(ch)
        except Exception:
            pass

    if ui_emitter and not any(isinstance(h, UILogHandler) for h in logger.handlers):
        uh = UILogHandler(ui_emitter)
        uh.setLevel(level)
        uh.setFormatter(fmt)
        logger.addHandler(uh)