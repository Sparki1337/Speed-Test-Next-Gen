# coding: utf-8
import os
import sys
import platform
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Импорты пакета (основной путь)
try:
    from .logging_utils import LogEmitter, setup_logging
    from .core.logging_system import get_logger, LogCategory
except ImportError:
    # Запасной путь: запуск из папки как скрипта
    from logging_utils import LogEmitter, setup_logging  # type: ignore
    from core.logging_system import get_logger, LogCategory  # type: ignore


def get_version():
    """Получить версию приложения."""
    try:
        try:
            from .version import __version__, __status__  # пакетный импорт
        except Exception:
            from version import __version__, __status__  # fallback при запуске из каталога
        return f"{__version__} {__status__}"
    except:
        return "Unknown"


def main():
    # Проверка ОС (только Windows 10/11)
    if platform.system().lower() != 'windows':
        print('Это приложение поддерживается только на Windows 10/11.')
        return

    # Логгер приложения (будет инициализирован позже с UI эмиттером)
    logger = None
    
    try:
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

        # Логирование с выводом в UI и настройки
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

        # Получить уровень логирования из настроек
        log_level_name = str(settings.get('log_level', 'INFO'))
        log_level = getattr(logging, log_level_name, logging.INFO)
        
        setup_logging(ui_emitter=emitter, level=log_level, enabled=True)
        
        # Теперь логгер доступен
        logger = get_logger(LogCategory.APP)
        logger.info("=" * 60)
        logger.info("Запуск приложения Fluent Speedtest", data={
            'version': get_version(),
            'platform': platform.platform(),
            'python_version': sys.version.split()[0],
            'qt_version': app.applicationVersion() or 'unknown'
        })
        logger.info(f"Тема: {theme_name}, Акцентный цвет: {accent_color}", data={
            'theme': theme_name,
            'accent_color': accent_color,
            'accent_hex': accent_hex
        })
        logger.info(f"Уровень логирования: {log_level_name}")
        
        # Импорт окна после создания QApplication
        try:
            from .app_window import AppWindow
        except ImportError:
            from app_window import AppWindow  # type: ignore

        logger.info("Создание главного окна приложения")
        w = AppWindow(emitter=emitter)
        
        logger.info("Отображение главного окна")
        w.show()
        
        logger.info("Приложение готово к работе")
        logger.info("=" * 60)
        
        exit_code = app.exec_()
        
        logger.info("Завершение работы приложения", data={'exit_code': exit_code})
        
        # Корректное завершение системы логирования
        from core.logging_system import get_logging_system
        get_logging_system().shutdown()
        
        sys.exit(exit_code)
        
    except Exception as e:
        # Критическая ошибка при запуске
        if logger:
            logger.error(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)
        else:
            print(f"Критическая ошибка при запуске приложения: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
