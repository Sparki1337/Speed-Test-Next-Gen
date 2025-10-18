# coding: utf-8
import logging
from threading import Event

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from .settings import get_settings
try:
    from .speedtest_service import SpeedtestService
except ImportError:  # fallback при локальном запуске
    from core.speedtest_service import SpeedtestService  # type: ignore

logger = logging.getLogger(__name__)


class SpeedtestWorker(QObject):
    
    # Фоновый исполнитель для запуска speedtest без блокировки GUI.
    # Прерывание происходит мягко (отмена применяется между этапами).

    stageChanged = pyqtSignal(str)       # init | servers | best | download | upload | saving | done | canceled | error
    log = pyqtSignal(str)
    resultReady = pyqtSignal(dict)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cancel_event = Event()
        self._settings = get_settings()


    @pyqtSlot()
    def cancel(self):
        self._cancel_event.set()
        # понизим уровень подробных сообщений в UI — используем debug вместо явного вывода
        logger.info('Отмена запрошена. Дождитесь завершения текущего этапа...')

    def _check_cancel(self):
        if self._cancel_event.is_set():
            self.stageChanged.emit('canceled')
            self.finished.emit()
            return True
        return False

    @pyqtSlot()
    def run(self):
        try:
            service = SpeedtestService(
                on_stage=lambda s: self.stageChanged.emit(s),
                on_log=lambda m: self.log.emit(m),
            )
            result = service.run_single_test(cancel_event=self._cancel_event)
            if self._check_cancel():
                return
            self.resultReady.emit(result)
            self.stageChanged.emit('done')
            self.finished.emit()
        except Exception as e:
            if self._cancel_event.is_set() or str(e).lower().startswith('отменено'):
                # Пользовательская отмена — не считаем ошибкой
                logger.info('Тест отменён пользователем')
                self.stageChanged.emit('canceled')
                self.finished.emit()
            else:
                logger.exception('Ошибка при запуске speedtest')
                self.stageChanged.emit('error')
                self.error.emit(str(e))
                self.finished.emit()


class PreciseSpeedtestWorker(QObject):
    
    # Последовательно выполняет 3 теста на разных серверах и отдаёт среднее значение.
    # При наличии избранных серверов использует их с приоритетом.

    stageChanged = pyqtSignal(str)       # init | servers | best | download | upload | saving | done | canceled | error
    log = pyqtSignal(str)
    resultReady = pyqtSignal(dict)       # средний результат по 3 прогонкам
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cancel_event = Event()
        self._settings = get_settings()

    @pyqtSlot()
    def cancel(self):
        self._cancel_event.set()
        logger.info('Отмена точного теста запрошена')

    def _check_cancel(self) -> bool:
        if self._cancel_event.is_set():
            self.stageChanged.emit('canceled')
            self.finished.emit()
            return True
        return False

    @pyqtSlot()
    def run(self):
        try:
            service = SpeedtestService(
                on_stage=lambda s: self.stageChanged.emit(s),
                on_log=lambda m: self.log.emit(m),
            )
            result = service.run_precise_test(cancel_event=self._cancel_event)
            if self._check_cancel():
                return
            self.resultReady.emit(result)
            self.stageChanged.emit('done')
            self.finished.emit()
        except Exception as e:
            if self._cancel_event.is_set():
                logger.info('Точный тест отменён пользователем')
                self.stageChanged.emit('canceled')
                self.finished.emit()
            else:
                logger.exception('Ошибка при выполнении точного теста')
                self.stageChanged.emit('error')
                self.error.emit(str(e))
                self.finished.emit()
