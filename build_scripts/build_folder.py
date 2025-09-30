#!/usr/bin/env python3
# coding: utf-8
"""
Скрипт сборки приложения Speedtest NextGen в папку (standalone) с помощью Nuitka.
Автоматически получает версию из version.py.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_version_from_file(project_root: Path) -> str:
    """Получить версию из version.py."""
    version_file = project_root / "version.py"
    if not version_file.exists():
        return None
    
    try:
        # Добавить project_root в sys.path для импорта
        sys.path.insert(0, str(project_root))
        from version import __version__
        return __version__
    except ImportError:
        return None
    finally:
        # Убрать из sys.path
        if str(project_root) in sys.path:
            sys.path.remove(str(project_root))


def build(version: str) -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    main_py = project_root / "main.py"
    icon_ico = project_root / "assets" / "app.ico"
    version_py = project_root / "version.py"

    print("="*60)
    print("🚀 Сборка Speedtest NextGen (Standalone)")
    print("="*60)

    if not main_py.exists():
        print(f"❌ [Ошибка] Не найден файл приложения: {main_py}")
        return 1

    if not icon_ico.exists():
        print(f"❌ [Ошибка] Не найден файл иконки: {icon_ico}")
        return 1
    
    if not version_py.exists():
        print(f"⚠️  [Предупреждение] Не найден файл version.py")
    
    print(f"✅ Файл приложения: {main_py.name}")
    print(f"✅ Иконка: {icon_ico.name}")
    print(f"✅ Версия: {version}")

    # Выбор компилятора для Nuitka: Python 3.13+ требует MSVC
    use_msvc = sys.version_info >= (3, 13)
    compiler_flag = "--msvc=latest" if use_msvc else "--mingw64"

    # Строгое выполнение через текущий интерпретатор: 'sys.executable -m nuitka'
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        compiler_flag,
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=platforms,styles,iconengines,imageformats,platformthemes,printsupport",
        "--include-package=qfluentwidgets",
        "--include-package-data=qfluentwidgets",
        "--include-package=qframelesswindow",
        "--include-package=openpyxl",
        "--include-package=speedtest",
        f"--windows-icon-from-ico={icon_ico}",
        "--windows-company-name=By Sparki",
        "--windows-product-name=SpeedTest Nextgen",
        "--windows-file-description=SpeedTest NextGen - Network Speed Test Tool",
        f"--windows-file-version={version}",
        f"--windows-product-version={version}",
        "--windows-console-mode=disable",
        "--output-dir=build",
        "--output-filename=SpeedTestNextgen",
        str(main_py),
    ]

    print(f"\n🔧 Компилятор: {'MSVC (latest)' if use_msvc else 'MinGW-w64'}")
    print(f"🐍 Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"\n📦 Включённые пакеты:")
    print("   - PyQt5 (GUI framework)")
    print("   - QFluentWidgets (Fluent Design)")
    print("   - openpyxl (Excel export)")
    print("   - speedtest-cli (Speed test engine)")
    
    print(f"\n⚙️  Запуск Nuitka...")
    print("="*60)
    
    try:
        result = subprocess.run(cmd, check=True, cwd=project_root)
        print("="*60)
        print("✅ Сборка завершена успешно!")
        print(f"📁 Результат: build/SpeedTestNextgen.dist/")
        print("="*60)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print("="*60)
        print(f"❌ [Ошибка] Nuitka завершилась с ошибкой, код: {e.returncode}")
        print("="*60)
        return e.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сборка проекта в папку (standalone) с помощью Nuitka",
    )
    parser.add_argument(
        "-v",
        "--version",
        dest="version",
        default=None,
        help="Версия приложения (например, 1.0.2). Если не указана, будет запрошена интерактивно.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    version = args.version
    
    # Если версия не указана, попробовать получить из version.py
    if not version:
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        version = get_version_from_file(project_root)
        
        if version:
            print(f"📦 Версия получена из version.py: {version}")
            use_version = input(f"Использовать эту версию? (y/n) [y]: ").strip().lower()
            if use_version and use_version != 'y':
                version = None
    
    # Если всё ещё нет версии, запросить у пользователя
    if not version:
        try:
            version = input("Введите версию приложения (например, 1.3.0): ").strip()
        except KeyboardInterrupt:
            print("\n❌ Отменено пользователем.")
            sys.exit(130)
    
    if not version:
        print("❌ [Ошибка] Версия не указана.")
        sys.exit(2)

    sys.exit(build(version=version))