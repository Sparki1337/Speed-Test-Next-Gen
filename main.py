# coding: utf-8
import os
import sys
import platform

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Импорты пакета (основной путь)
try:
    from .logging_utils import LogEmitter, setup_logging
except ImportError:
    # Запасной путь: запуск из папки как скрипта
    from logging_utils import LogEmitter, setup_logging  # type: ignore


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
        from qfluentwidgets import setTheme, Theme, setThemeColor
        from PyQt5.QtGui import QColor
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
    
    # Применить акцентный цвет
    accent_color = str(settings.get('accent_color', 'blue'))
    colors = {
        'blue': '#0078D4',
        'green': '#10893E',
        'purple': '#881798',
        'red': '#E81123',
        'orange': '#FF8C00',
        'pink': '#E3008C'
    }
    accent_hex = colors.get(accent_color, '#0078D4')
    try:
        setThemeColor(QColor(accent_hex))
    except Exception:
        pass

    setup_logging(ui_emitter=emitter, enabled=True)

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
