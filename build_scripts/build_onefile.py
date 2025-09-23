#!/usr/bin/env python3
# coding: utf-8

import argparse
import subprocess
import sys
from pathlib import Path


def build(version: str) -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    main_py = project_root / "main.py"
    icon_ico = project_root / "assets" / "app.ico"

    if not main_py.exists():
        print(f"[Ошибка] Не найден файл приложения: {main_py}")
        return 1

    if not icon_ico.exists():
        print(f"[Ошибка] Не найден файл иконки: {icon_ico}")
        return 1

    # Выбор компилятора для Nuitka: Python 3.13+ требует MSVC
    use_msvc = sys.version_info >= (3, 13)
    compiler_flag = "--msvc=latest" if use_msvc else "--mingw64"

    # Строгое выполнение через текущий интерпретатор: 'sys.executable -m nuitka'
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--standalone",
        compiler_flag,
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=platforms,styles,iconengines,imageformats,platformthemes,printsupport",
        "--include-package=qfluentwidgets",
        "--include-package-data=qfluentwidgets",
        "--include-package=qframelesswindow",
        f"--windows-icon-from-ico={icon_ico}",
        "--windows-company-name=By Sparki",
        "--windows-product-name=SpeedTest Nextgen",
        "--windows-file-description=SpeedTest",
        f"--windows-file-version={version}",
        f"--windows-product-version={version}",
        "--windows-console-mode=disable",
        "--output-dir=build",
        "--output-filename=SpeedTestNextgen",
        str(main_py),
    ]

    print(f"[Info] Компилятор: {'MSVC (latest)' if use_msvc else 'MinGW-w64'} (Python {sys.version_info.major}.{sys.version_info.minor})")
    print("[Info] Запускаю Nuitka со следующей командой:\n" + " ".join(map(str, cmd)))
    try:
        result = subprocess.run(cmd, check=True, cwd=project_root)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"[Ошибка] Nuitka завершилась с ошибкой, код: {e.returncode}")
        return e.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сборка проекта в один файл (onefile) с помощью Nuitka",
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
    if not version:
        try:
            version = input("Введите версию приложения (например, 1.0.2): ").strip()
        except KeyboardInterrupt:
            print("\nОтменено пользователем.")
            sys.exit(130)
    if not version:
        print("[Ошибка] Версия не указана.")
        sys.exit(2)

    sys.exit(build(version=version))
