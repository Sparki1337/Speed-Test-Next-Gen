# coding: utf-8
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

from PyQt5.QtCore import QObject, pyqtSignal


APP_FOLDER_NAME = "SpeedtestNextGen"
SETTINGS_FILENAME = "settings.json"


def documents_dir() -> Path:
    # Папка Документы пользователя
    return Path.home() / "Documents"


def settings_path() -> Path:
    return documents_dir() / APP_FOLDER_NAME / SETTINGS_FILENAME


_DEFAULTS: Dict[str, Any] = {
    "units": "Mbps",         # Mbps | MB/s
    "theme": "Dark",         # Dark | Light
    "favorite_server_ids": [],  # список избранных серверов (IDs)
    "engine": "python",      # Движок измерения: 'python' (встроенная библиотека speedtest-cli) | 'ookla' (официальный speedtest.exe)
    "ookla_path": "",        # Путь к speedtest.exe (если пусто — ищется в PATH)
    "ookla_timeout": 90,     # Таймаут выполнения speedtest.exe (секунды)
    "accent_color": "blue",  # Акцентный цвет: blue | green | purple | red | orange | pink
    "max_history_records": 1000,  # Максимальное количество записей в истории
}


class SettingsManager(QObject):
    changed = pyqtSignal(str, object)  # key, value

    def __init__(self):
        super().__init__()
        self._data: Dict[str, Any] = {}
        self._path = settings_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        # применяем значения по умолчанию
        for k, v in _DEFAULTS.items():
            self._data.setdefault(k, v)
        # флаг логов всегда принудительно включён
        self._data['logs_enabled'] = True

    def save(self) -> None:
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self.save()
        self.changed.emit(key, value)


# синглтон
_settings_singleton: SettingsManager | None = None


def get_settings() -> SettingsManager:
    global _settings_singleton
    if _settings_singleton is None:
        _settings_singleton = SettingsManager()
    return _settings_singleton
