#!/usr/bin/env python3
# coding: utf-8
"""
Скрипт для управления версией и статусом приложения.
Использование:
    python set_version.py --version 1.3.0 --status Beta
    python set_version.py --status Stable
"""

import argparse
import re
from pathlib import Path


def update_version_file(version: str = None, status: str = None):
    """Обновить файл version.py."""
    version_file = Path(__file__).parent / "version.py"
    
    if not version_file.exists():
        print(f"❌ Файл {version_file} не найден!")
        return False
    
    content = version_file.read_text(encoding="utf-8")
    
    # Обновить версию
    if version:
        content = re.sub(
            r'__version__\s*=\s*"[^"]*"',
            f'__version__ = "{version}"',
            content
        )
        print(f"✅ Версия обновлена: {version}")
    
    # Обновить статус
    if status:
        if status not in ["Beta", "Stable", "RC"]:
            print(f"❌ Неверный статус: {status}. Используйте: Beta, Stable, RC")
            return False
        
        content = re.sub(
            r'__status__\s*=\s*"[^"]*"',
            f'__status__ = "{status}"',
            content
        )
        print(f"✅ Статус обновлён: {status}")
    
    # Сохранить изменения
    version_file.write_text(content, encoding="utf-8")
    print(f"💾 Файл {version_file.name} сохранён")
    
    return True


def show_current_version():
    """Показать текущую версию."""
    try:
        from version import __version__, __status__, get_version_string
        print(f"\n📦 Текущая версия: {get_version_string()}")
        print(f"   Номер версии: {__version__}")
        print(f"   Статус: {__status__}\n")
    except ImportError:
        print("❌ Не удалось импортировать version.py")


def main():
    parser = argparse.ArgumentParser(
        description="Управление версией приложения Speedtest NextGen"
    )
    parser.add_argument(
        "--version", "-v",
        type=str,
        help="Установить номер версии (например: 1.3.0)"
    )
    parser.add_argument(
        "--status", "-s",
        type=str,
        choices=["Beta", "Stable", "RC"],
        help="Установить статус релиза"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Показать текущую версию"
    )
    
    args = parser.parse_args()
    
    if args.show or (not args.version and not args.status):
        show_current_version()
        return
    
    if update_version_file(args.version, args.status):
        print("\n" + "="*50)
        show_current_version()
        print("="*50)
        print("\n💡 Не забудьте закоммитить изменения:")
        print(f"   git add version.py")
        if args.version:
            print(f'   git commit -m "chore: bump version to {args.version}"')
        if args.status:
            print(f'   git commit -m "chore: set status to {args.status}"')


if __name__ == "__main__":
    main()
