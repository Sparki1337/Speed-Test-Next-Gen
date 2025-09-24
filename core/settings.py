# coding: utf-8
from __future__ import annotations
import json
import logging
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


logger = logging.getLogger(__name__)


_DEFAULTS: Dict[str, Any] = {
    "units": "Mbps",         # Mbps | MB/s
    "theme": "Dark",         # Dark | Light
    "logs_enabled": True,     # Включены ли логи (UI + консоль)
    "favorite_server_ids": [],  # список избранных серверов (IDs)
}


class SettingsManager(QObject):
    changed = pyqtSignal(str, object)  # key, value

    def __init__(self):
        super().__init__()
        self._data: Dict[str, Any] = {}
        self._path = settings_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _backup_corrupted_file(self) -> Path | None:
        try:
            base = self._path.parent / f"{self._path.name}.bak"
            if not base.exists():
                self._path.rename(base)
                return base
            idx = 1
            while True:
                candidate = self._path.parent / f"{self._path.name}.bak{idx}"
                if not candidate.exists():
                    self._path.rename(candidate)
                    return candidate
                idx += 1
        except Exception as exc:
            logger.warning("Не удалось создать резервную копию повреждённого файла настроек: %s", exc)
        return None

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                backup_path = self._backup_corrupted_file()
                self._data = {}
                if backup_path is not None:
                    logger.warning(
                        "Файл настроек повреждён и был перемещён в '%s'. Будут использованы значения по умолчанию.",
                        backup_path,
                    )
                else:
                    logger.warning(
                        "Файл настроек повреждён и будет перезаписан значениями по умолчанию: %s",
                        exc,
                    )
        # применяем значения по умолчанию
        for k, v in _DEFAULTS.items():
            self._data.setdefault(k, v)

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
