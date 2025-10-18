# coding: utf-8
import logging
from datetime import datetime
from typing import Callable, Optional, List
import threading

try:
    from .settings import get_settings
    from .speedtest_client import SpeedtestClient
    from .ookla_client import OoklaCliClient
    from .storage import append_result
    from .logging_system import get_logger, LogCategory
except ImportError:  # локальный запуск
    from core.settings import get_settings  # type: ignore
    from core.speedtest_client import SpeedtestClient  # type: ignore
    from core.ookla_client import OoklaCliClient  # type: ignore
    from core.storage import append_result  # type: ignore
    from core.logging_system import get_logger, LogCategory  # type: ignore


_py_logger = logging.getLogger(__name__)


class SpeedtestService:
    """
    Сервисный слой оркестрации измерений скорости.
    Задачи сервиса:
    - Выбор движка (python | ookla)
    - Запуск измерения и агрегаций (обычный и точный сценарии)
    - Обработка и нормализация результатов
    - Сохранение результатов в хранилище
    - Уведомления о стадиях/логах через колбэки (без привязки к UI)
    """

    def __init__(
        self,
        on_stage: Optional[Callable[[str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.settings = get_settings()
        self.on_stage = on_stage
        self.on_log = on_log
        self.logger = get_logger(LogCategory.TEST)

    # Вспомогательные уведомления
    def _emit_stage(self, stage: str) -> None:
        try:
            if self.on_stage:
                self.on_stage(stage)
        finally:
            pass

    def _emit_log(self, text: str) -> None:
        try:
            if self.on_log:
                self.on_log(text)
        finally:
            pass

    def _format_speed(self, bps: float) -> str:
        units = self.settings.get('units', 'Mbps')
        if units == 'MB/s':
            return f"{bps / 8e6:.2f} MB/s"
        return f"{bps / 1e6:.2f} Mbps"

    def _select_client(self):
        engine = str(self.settings.get('engine', 'python')).lower()
        if engine == 'ookla':
            self._emit_log('Движок: Ookla CLI')
            _py_logger.info('Движок: Ookla CLI')
            return 'ookla', OoklaCliClient()
        self._emit_log('Движок: Python speedtest-cli')
        _py_logger.info('Движок: Python speedtest-cli')
        return 'python', SpeedtestClient()

    def run_single_test(
        self,
        cancel_event: Optional[threading.Event] = None,
        server_id_override: Optional[int] = None,
    ) -> dict:
        """
        Выполнить одиночный тест скорости и сохранить результат.
        Возвращает результат измерения.
        """
        self._emit_stage('init')
        self.logger.info('Запуск одиночного теста скорости')
        self._emit_log('Запуск теста скорости...')

        # Стадии UI для совместимости
        self._emit_stage('servers')
        self._emit_stage('best')

        engine_name, client = self._select_client()

        # Запускаем собственно измерение
        self._emit_stage('download')
        result = client.perform_test(cancel_event=cancel_event, server_id_override=server_id_override)

        # Нормализуем поля
        if 'timestamp' not in result or not result['timestamp']:
            result['timestamp'] = datetime.now().isoformat(timespec='seconds')
        if 'engine' not in result:
            result['engine'] = engine_name

        # Короткое резюме в логах
        try:
            ping = float(result.get('ping_ms', 0))
            d_bps = float(result.get('download_bps', 0.0))
            u_bps = float(result.get('upload_bps', 0.0))
            s = result.get('server', {}) or {}
            sponsor = s.get('sponsor', '-')
            name = s.get('name', '-')
            country = s.get('country', '-')
            host = s.get('host', '-')
            sid = s.get('id', '-')
            self.logger.info(
                'Тест завершён',
                data={
                    'ping_ms': ping,
                    'download_mbps': d_bps / 1e6 if d_bps else 0.0,
                    'upload_mbps': u_bps / 1e6 if u_bps else 0.0,
                    'server_id': sid,
                    'server': f"{sponsor} — {name}, {country} ({host})",
                    'engine': engine_name,
                },
            )
            self._emit_log(
                f"Итог: Ping {ping:.0f} ms | Download {self._format_speed(d_bps)} | "
                f"Upload {self._format_speed(u_bps)} | Сервер: {sponsor} — {name}, {country} "
                f"({host}) [ID {sid}]"
            )
        except Exception:
            pass

        # Сохранение
        self._emit_stage('saving')
        try:
            append_result(result)
        except Exception:
            # не срываем выполнение из-за проблем хранения
            _py_logger.exception('Не удалось сохранить результат теста')

        return result

    # ---- Точный сценарий ----
    def _pick_three_server_ids(self) -> List[int]:
        # 1) избранные из настроек
        fav_ids: List[int] = []
        try:
            fav_ids = [int(x) for x in (self.settings.get('favorite_server_ids', []) or [])]
        except Exception:
            fav_ids = []

        seen = set()
        picked: List[int] = []
        for sid in fav_ids:
            if sid and sid not in seen:
                picked.append(sid)
                seen.add(sid)
                if len(picked) >= 3:
                    return picked[:3]

        # 2) добираем из общего списка
        try:
            st_client = SpeedtestClient()
            servers = st_client.list_servers(limit=300)
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
            pass
        return picked[:3]

    def run_precise_test(
        self,
        cancel_event: Optional[threading.Event] = None,
    ) -> dict:
        """
        Выполнить «точный» тест: 3 прогона на разных серверах. Возвращает агрегированный результат.
        Также сразу сохраняет агрегированный результат.
        """
        self._emit_stage('init')
        self.logger.info('Запуск точного теста (3 прогона)')
        self._emit_log('Запуск точного теста (3 прогона на разных серверах)...')

        server_ids = self._pick_three_server_ids()
        if len(server_ids) < 3:
            self._emit_log('Недостаточно доступных серверов, будет использовано меньше 3.')

        results: List[dict] = []
        for idx, sid in enumerate(server_ids):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError('Отменено пользователем')
            self._emit_stage('servers')
            self._emit_log(f'[{idx+1}/3] Тест на сервере ID={sid}...')
            _engine_name, client = self._select_client()
            self._emit_stage('download')
            res = client.perform_test(cancel_event=cancel_event, server_id_override=sid)
            if 'engine' not in res:
                res['engine'] = _engine_name
            results.append(res)

        # Если серверов было меньше 3 — добираем автоматическим выбором
        while len(results) < 3 and (cancel_event is None or not cancel_event.is_set()):
            self._emit_stage('servers')
            self._emit_log(f'[{len(results)+1}/3] Тест с автоматическим выбором сервера...')
            _engine_name, client = self._select_client()
            self._emit_stage('download')
            res = client.perform_test(cancel_event=cancel_event, server_id_override=None)
            if 'engine' not in res:
                res['engine'] = _engine_name
            results.append(res)

        # Агрегация
        self._emit_stage('saving')
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

        # Сохранить агрегированный результат
        try:
            append_result(avg_result)
        except Exception:
            _py_logger.exception('Не удалось сохранить агрегированный результат')

        # Лог-резюме
        try:
            self.logger.info(
                'Точный тест завершён',
                data={
                    'samples': len(results),
                    'ping_ms_avg': ping_avg,
                    'download_mbps_avg': d_avg / 1e6 if d_avg else 0.0,
                    'upload_mbps_avg': u_avg / 1e6 if u_avg else 0.0,
                },
            )
            self._emit_log(
                f"Среднее: Ping {ping_avg:.0f} ms | Download {self._format_speed(d_avg)} | "
                f"Upload {self._format_speed(u_avg)}"
            )
        except Exception:
            pass

        return avg_result


