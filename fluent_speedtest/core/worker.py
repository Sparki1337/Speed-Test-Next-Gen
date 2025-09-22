# coding: utf-8
import logging
from threading import Event

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from .speedtest_client import SpeedtestClient
from .settings import get_settings

logger = logging.getLogger(__name__)


class SpeedtestWorker(QObject):
    """
    Фоновый исполнитель для запуска speedtest без блокировки GUI.
    Прерывание происходит мягко (отмена применяется между этапами).
    """

    stageChanged = pyqtSignal(str)       # init | servers | best | download | upload | saving | done | canceled | error
    log = pyqtSignal(str)
    resultReady = pyqtSignal(dict)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cancel_event = Event()
        self._settings = get_settings()

    def _format_speed(self, bps: float) -> str:
        units = self._settings.get('units', 'Mbps')
        if units == 'MB/s':
            return f"{bps / 8e6:.2f} MB/s"
        return f"{bps / 1e6:.2f} Mbps"

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
            client = SpeedtestClient()

            self.stageChanged.emit('init')
            logger.info('Запуск теста скорости...')
            if self._check_cancel():
                return

            self.stageChanged.emit('servers')
            # Подробные этапы логируются внутри SpeedtestClient

            if self._check_cancel():
                return

            self.stageChanged.emit('best')
            if self._check_cancel():
                return

            self.stageChanged.emit('download')
            result = client.perform_test(cancel_event=self._cancel_event)  # включает download и upload

            if self._check_cancel():
                return

            self.stageChanged.emit('saving')
            # Красивое резюме результатов в лог
            try:
                ping = float(result.get('ping_ms', 0))
                d_bps = float(result.get('download_bps', 0.0))
                u_bps = float(result.get('upload_bps', 0.0))
                s = result.get('server', {})
                sponsor = s.get('sponsor', '-')
                name = s.get('name', '-')
                country = s.get('country', '-')
                host = s.get('host', '-')
                sid = s.get('id', '-')
                ts = result.get('timestamp', '-')

                logger.info(
                    f"Итог: Ping {ping:.0f} ms | Download {self._format_speed(d_bps)} | "
                    f"Upload {self._format_speed(u_bps)} | Сервер: {sponsor} — {name}, {country} "
                    f"({host}) [ID {sid}] | {ts}"
                )
            except Exception:
                # не срываем пайплайн, если форматирование не удалось
                pass
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
