# coding: utf-8
import logging
from datetime import datetime
import threading

import speedtest

logger = logging.getLogger(__name__)

try:
    from .settings import get_settings
except ImportError:
    from core.settings import get_settings  # type: ignore

class SpeedtestClient:
    # Обёртка над speedtest-cli для получения ping/down/up и информации о сервере

    def __init__(self):
        self.settings = get_settings()
        self._ua_patched = False

    def _monkeypatch_user_agent(self):
        # Пробуем подменить User-Agent на браузерный для обхода возможного 403 от Cloudflare.
        # Библиотека speedtest-cli использует функцию build_user_agent() для установки заголовка.
        # Мы мягко меняем её, если доступна.
        if self._ua_patched:
            return
        try:
            if hasattr(speedtest, 'build_user_agent'):
                logger.warning('Пробую обойти 403: устанавливаю браузерный User-Agent...')
                def _ua(*_a, **_kw):
                    return (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0 Safari/537.36'
                    )
                speedtest.build_user_agent = _ua  # type: ignore[attr-defined]
                self._ua_patched = True
        except Exception:
            # Не критично, продолжаем без патча
            pass

    def _create_speedtest(self) -> "speedtest.Speedtest":
        # Создать экземпляр Speedtest с повторными попытками и обходом 403.
        # Последовательность попыток:
        # 1) Обычная инициализация
        # 2) Повтор с переключением secure=True/False
        # 3) Патч User-Agent и снова попытки
        
        last_err: Exception | None = None

        def _try_variants():
            # Пробуем разные варианты secure
            variants = [
                {},
                {"secure": True},
                {"secure": False},
            ]
            for kwargs in variants:
                try:
                    return speedtest.Speedtest(**kwargs)
                except Exception as e:  # сохраняем и пробуем далее
                    nonlocal last_err
                    last_err = e
            return None

        # 1) Базовые попытки
        st = _try_variants()
        if st is not None:
            return st

        # 2) Если встречали 403 — патчим UA и пробуем ещё раз
        if last_err and ('403' in str(last_err) or 'Forbidden' in str(last_err)):
            self._monkeypatch_user_agent()
            st = _try_variants()
            if st is not None:
                return st

        # 3) Не удалось
        assert last_err is not None
        raise last_err

    def perform_test(self, cancel_event: threading.Event | None = None, server_id_override: int | None = None):
        logger.info('Инициализация клиента Speedtest...')
        s = self._create_speedtest()

        # Монитор отмены: если cancel_event установлен, прервать текущий сетевой этап speedtest
        cancel_monitor = None
        if cancel_event is not None:
            def _watch_cancel():
                cancel_event.wait()
                try:
                    # внутренний флаг библиотеки speedtest-cli, останавливает download/upload
                    s._shutdown_event.set()
                    logger.info('Отмена: прерываю текущий сетевой этап...')
                except Exception:
                    pass

            cancel_monitor = threading.Thread(target=_watch_cancel, name='st-cancel-watch', daemon=True)
            cancel_monitor.start()

        # выбрать сервер: приоритет у параметра server_id_override, иначе из настроек
        server_id = server_id_override if server_id_override is not None else self.settings.get('server_id', None)
        if server_id:
            try:
                sid = int(server_id)
            except Exception:
                sid = None
        else:
            sid = None

        used_custom = False
        if sid:
            logger.info(f'Использую выбранный сервер ID={sid}...')
            try:
                s.get_servers([sid])
                used_custom = True
            except speedtest.NoMatchedServers:
                logger.warning(f'Сервер ID={sid} не найден среди доступных. Перехожу к автоматическому выбору.')
                s.get_servers([])
                used_custom = False
            except Exception as e:
                logger.warning(f'Не удалось получить сервер ID={sid}: {e}. Перехожу к автоматическому выбору.')
                s.get_servers([])
                used_custom = False
        else:
            logger.info('Получение списка серверов...')
            s.get_servers([])

        if used_custom:
            logger.info('Подтверждение выбранного сервера...')
        else:
            logger.info('Выбор лучшего сервера...')
        best = s.get_best_server()
        sponsor = best.get('sponsor')
        name = best.get('name')
        cc = best.get('country')
        host = best.get('host')
        sid_best = best.get('id')
        if used_custom:
            logger.info(f"Выбран сервер: {sponsor} — {name}, {cc} ({host}) [ID {sid_best}]")
        else:
            logger.info(f"Лучший сервер: {sponsor} — {name}, {cc} ({host}) [ID {sid_best}]")

        # Проверить отмену перед началом download
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('Отменено пользователем')

        logger.info('Тест загрузки (download)...')
        d_bps = s.download()

        # Проверить отмену перед началом upload
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('Отменено пользователем')

        logger.info('Тест отдачи (upload)...')
        u_bps = s.upload()

        ping_ms = s.results.ping

        result = {
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'ping_ms': float(ping_ms),
            'download_bps': float(d_bps),
            'upload_bps': float(u_bps),
            'server': {
                'id': sid_best,
                'sponsor': sponsor,
                'name': name,
                'country': cc,
                'host': host,
            },
        }
        logger.info('Тест завершён успешно')
        return result

    def list_servers(self, limit: int = 200):
        # Получить список доступных серверов (упрощённый вид для UI).
        # Возвращает список словарей: id, sponsor, name (city), country, host
        s = self._create_speedtest()
        s.get_servers([])
        servers = []
        # Speedtest.servers — dict {distance: [server_dict, ...]}
        for _, entries in s.servers.items():
            for sv in entries:
                servers.append({
                    'id': int(sv.get('id')) if sv.get('id') is not None else None,
                    'sponsor': sv.get('sponsor', ''),
                    'name': sv.get('name', ''),
                    'country': sv.get('country', ''),
                    'host': sv.get('host', ''),
                })
                if len(servers) >= limit:
                    break
            if len(servers) >= limit:
                break
        # уникализировать по id, сохраняя порядок
        seen = set()
        uniq = []
        for sv in servers:
            sid = sv['id']
            if sid in seen:
                continue
            seen.add(sid)
            uniq.append(sv)
        return uniq

