# coding: utf-8
import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .settings import get_settings
except ImportError:
    from core.settings import get_settings  # type: ignore


logger = logging.getLogger(__name__)


class OoklaCliClient:
    """
    Клиент для запуска официального Ookla Speedtest CLI (speedtest.exe) и парсинга JSON-результата.

    Возвращаемый формат результата совместим с ожидаемым UI/хранилищем:
    {
      'timestamp': str,
      'ping_ms': float,
      'download_bps': float,
      'upload_bps': float,
      'server': {
        'id': int | str,
        'sponsor': str,   # провайдер (из поля name у Ookla)
        'name': str,      # город/локация (из поля location у Ookla)
        'country': str,
        'host': str,
      },
      'engine': 'ookla'
    }
    """

    def __init__(self):
        self.settings = get_settings()

    def _resolve_binary(self) -> str:
        configured: str = str(self.settings.get('ookla_path', '') or '').strip()
        if configured:
            p = Path(configured)
            if p.exists() and p.is_file():
                return str(p)
            raise FileNotFoundError(f"Не найден speedtest.exe по пути: {configured}")
        # если путь не указан, рассчитываем, что он есть в PATH
        return 'speedtest'

    def _build_command(self, server_id: Optional[int]) -> list[str]:
        cmd = [
            self._resolve_binary(),
            '--accept-license',
            '--accept-gdpr',
            '--format=json',
        ]
        if server_id:
            cmd.extend(['--server-id', str(server_id)])
        return cmd

    def perform_test(self, cancel_event: threading.Event | None = None, server_id_override: int | None = None) -> dict:
        # Определяем сервер
        server_id = server_id_override if server_id_override is not None else self.settings.get('server_id', None)
        try:
            sid = int(server_id) if server_id is not None else None
        except Exception:
            sid = None

        # Команда
        cmd = self._build_command(sid)
        timeout_sec =  int(self.settings.get('ookla_timeout', 90) or 90)

        logger.info('Инициализация клиента Ookla Speedtest CLI...')
        logger.info('Запуск теста через Ookla CLI...')

        # Старт процесса
        creationflags = 0
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creationflags = subprocess.CREATE_NO_WINDOW  # скрыть консоль на Windows

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            creationflags=creationflags,
        )

        # Монитор отмены
        cancel_thread: Optional[threading.Thread] = None
        if cancel_event is not None:
            def _watch_cancel():
                cancel_event.wait()
                if cancel_event.is_set():
                    try:
                        logger.info('Отмена: завершаю процесс speedtest.exe...')
                        proc.terminate()
                    except Exception:
                        pass
            cancel_thread = threading.Thread(target=_watch_cancel, name='ookla-cancel-watch', daemon=True)
            cancel_thread.start()

        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            raise RuntimeError(f"Таймаут выполнения Ookla CLI ({timeout_sec} сек)")

        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('Отменено пользователем')

        # Проверка кода возврата
        if proc.returncode != 0:
            err = (stderr or '').strip() or (stdout or '').strip()
            raise RuntimeError(f"Ошибка запуска Ookla CLI: {err}")

        # Извлекаем JSON (на всякий случай берём последнюю непустую строку)
        data_line = ''
        for line in (stdout or '').splitlines():
            line = line.strip()
            if not line:
                continue
            data_line = line
        if not data_line:
            raise RuntimeError('Пустой вывод от Ookla CLI — нет данных JSON')

        try:
            data = json.loads(data_line)
        except Exception as e:
            raise RuntimeError(f"Не удалось распарсить JSON от Ookla CLI: {e}")

        # Маппинг результата
        # По выводу Ookla CLI: download.bandwidth и upload.bandwidth — это БАЙТ/сек, конвертируем в бит/сек
        def to_bps(section: dict) -> float:
            bw = section.get('bandwidth')
            if bw is not None:
                try:
                    return float(bw) * 8.0
                except Exception:
                    pass
            # запасной путь: bytes/elapsed(ms)
            try:
                bytes_val = float(section.get('bytes', 0.0))
                elapsed_ms = float(section.get('elapsed', 0.0))
                if elapsed_ms > 0:
                    return bytes_val * 8.0 / (elapsed_ms / 1000.0)
            except Exception:
                pass
            return 0.0

        ping_ms = 0.0
        try:
            ping_ms = float(((data or {}).get('ping') or {}).get('latency', 0.0))
        except Exception:
            ping_ms = 0.0

        download_bps = to_bps((data or {}).get('download') or {})
        upload_bps = to_bps((data or {}).get('upload') or {})

        srv = (data or {}).get('server') or {}
        host = srv.get('host', '')
        port = srv.get('port')
        if port:
            try:
                host = f"{host}:{int(port)}"
            except Exception:
                pass

        result = {
            'timestamp': (data.get('timestamp') or datetime.now().isoformat(timespec='seconds')),
            'ping_ms': ping_ms,
            'download_bps': download_bps,
            'upload_bps': upload_bps,
            'server': {
                'id': srv.get('id'),
                'sponsor': srv.get('name') or '',
                'name': srv.get('location') or '',
                'country': srv.get('country') or '',
                'host': host,
            },
            'engine': 'ookla',
        }

        logger.info('Тест (Ookla CLI) завершён успешно')
        return result
