# coding: utf-8
import os
import sys
import platform

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Импорты пакета (основной путь)
try:
    from .logging_utils import LogEmitter, setup_logging, apply_logging_enabled
except ImportError:
    # Запасной путь: запуск из папки как скрипта
    from logging_utils import LogEmitter, setup_logging, apply_logging_enabled  # type: ignore


def main():
    # Проверка ОС (только Windows 10/11)
    if platform.system().lower() != 'windows':
        print('Это приложение поддерживается только на Windows 10/11.')
        return

    # Включить HiDPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName('Fluent Speedtest')
    app.setOrganizationName('FluentSpeed')

    # Импорт qfluentwidgets после создания QApplication
    try:
        from qfluentwidgets import setTheme, Theme
    except Exception:
        print('Требуется установленный пакет PyQt-Fluent-Widgets. Установите его и попробуйте снова.')
        return

    # Логирование с выводом в UI и настройки (хранятся в C:/Users/<User>/Documents/SpeedtestNextGen/settings.json)
    emitter = LogEmitter()
    # Настройки (хранятся в C:/Users/<User>/Documents/SpeedtestNextGen/settings.json)
    try:
        from .core.settings import get_settings
    except ImportError:
        from core.settings import get_settings  # type: ignore

    settings = get_settings()
    # Применить тему из настроек
    theme_name = str(settings.get('theme', 'Dark'))
    if theme_name == 'Dark':
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.LIGHT)

    logs_enabled = bool(settings.get('logs_enabled', True))
    setup_logging(ui_emitter=emitter, enabled=logs_enabled)

    # Реакция на динамическое изменение флага логов из настроек
    def _on_setting_changed(key: str, value):
        if key == 'logs_enabled':
            apply_logging_enabled(bool(value), ui_emitter=emitter)

    settings.changed.connect(_on_setting_changed)

    # Импорт окна после создания QApplication
    try:
        from .app_window import AppWindow
    except ImportError:
        from app_window import AppWindow  # type: ignore

    w = AppWindow(emitter=emitter)
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
