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


class PreciseSpeedtestWorker(QObject):
    """
    Последовательно выполняет 3 теста на разных серверах и отдаёт среднее значение.
    При наличии избранных серверов использует их с приоритетом.
    """

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

    def _pick_three_server_ids(self) -> list[int]:
        # 1) избранные из настроек
        fav_ids = []
        try:
            fav_ids = [int(x) for x in (self._settings.get('favorite_server_ids', []) or [])]
        except Exception:
            fav_ids = []
        seen = set()
        picked: list[int] = []
        for sid in fav_ids:
            if sid and sid not in seen:
                picked.append(sid)
                seen.add(sid)
                if len(picked) >= 3:
                    return picked[:3]

        # 2) если не хватило — добираем из общего списка
        try:
            client = SpeedtestClient()
            servers = client.list_servers(limit=300)
            for sv in servers:
                sid = sv.get('id')
                if not sid:
                    continue
                sid = int(sid)
                if sid in seen:
                    continue
                picked.append(sid)
                seen.add(sid)
                if len(picked) >= 3:
                    break
        except Exception:
            # если совсем не удалось получить список — вернём то, что есть
            pass
        return picked[:3]

    @pyqtSlot()
    def run(self):
        try:
            self.stageChanged.emit('init')
            logger.info('Запуск точного теста (3 прогона на разных серверах)...')
            if self._check_cancel():
                return

            # Выбираем 3 сервера
            server_ids = self._pick_three_server_ids()
            if len(server_ids) < 3:
                logger.warning('Недостаточно доступных серверов для точного теста, будет использовано меньше 3.')

            results: list[dict] = []
            client = SpeedtestClient()

            for idx, sid in enumerate(server_ids):
                if self._check_cancel():
                    return
                self.stageChanged.emit('servers')
                logger.info(f'[{idx+1}/3] Тест на сервере ID={sid}...')
                self.stageChanged.emit('download')
                res = client.perform_test(cancel_event=self._cancel_event, server_id_override=sid)
                results.append(res)

            if self._check_cancel():
                return

            # Если серверов было меньше 3 (редкий случай), дотестируем оставшиеся автоматическим выбором
            while len(results) < 3 and not self._cancel_event.is_set():
                self.stageChanged.emit('servers')
                logger.info(f'[{len(results)+1}/3] Тест с автоматическим выбором сервера...')
                self.stageChanged.emit('download')
                res = client.perform_test(cancel_event=self._cancel_event, server_id_override=None)
                results.append(res)

            if self._check_cancel():
                return

            self.stageChanged.emit('saving')
            # Подсчёт среднего
            try:
                ping_avg = sum(float(r.get('ping_ms', 0.0)) for r in results) / max(1, len(results))
                d_avg = sum(float(r.get('download_bps', 0.0)) for r in results) / max(1, len(results))
                u_avg = sum(float(r.get('upload_bps', 0.0)) for r in results) / max(1, len(results))
            except Exception:
                ping_avg, d_avg, u_avg = 0.0, 0.0, 0.0

            avg_result = {
                'timestamp': 'avg',
                'ping_ms': ping_avg,
                'download_bps': d_avg,
                'upload_bps': u_avg,
                'aggregate': True,
                'samples': len(results),
            }

            self.resultReady.emit(avg_result)
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
