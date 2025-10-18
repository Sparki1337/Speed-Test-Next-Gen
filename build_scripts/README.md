# 🔨 Инструкция по сборке Speedtest NextGen

## 📋 Требования

Перед сборкой убедитесь, что установлено:

```bash
# 1. Установить Nuitka
pip install nuitka

# 2. Для Python 3.13+ нужен MSVC (Visual Studio Build Tools)
# Скачать: https://visualstudio.microsoft.com/downloads/

# 3. Для Python 3.12 и ниже нужен MinGW-w64
# Скачать: https://winlibs.com/
```

---

## 🚀 Быстрый старт

### Вариант 1: Сборка в папку (рекомендуется для разработки)

```bash
# Запустить скрипт (версия берётся из version.py автоматически)
python build_scripts\build_folder.py

# Результат: build/SpeedTestNextgen.dist/SpeedTestNextgen.exe
```

**Преимущества:**
- ✅ Быстрая сборка (5-10 минут)
- ✅ Легко отлаживать
- ✅ Можно заменять отдельные файлы

**Недостатки:**
- ❌ Много файлов в папке
- ❌ Нужно распространять всю папку

---

### Вариант 2: Сборка в один файл (для релиза)

```bash
# Запустить скрипт
python build_scripts\build_onefile.py

# Результат: build/SpeedTestNextgen.exe
```

**Преимущества:**
- ✅ Один файл .exe
- ✅ Удобно распространять

**Недостатки:**
- ❌ Медленная сборка (10-15 минут)
- ❌ Больший размер файла
- ❌ Медленнее запускается

---

## 🎯 Использование

### Автоматическое определение версии

Скрипты автоматически читают версию из `version.py`:

```bash
python build_scripts\build_folder.py
# >>> 📦 Версия получена из version.py: 1.3.0
# >>> Использовать эту версию? (y/n) [y]:
```

Просто нажмите Enter для подтверждения.

### Указать версию вручную

```bash
# Через аргумент командной строки
python build_scripts\build_folder.py -v 1.3.0
python build_scripts\build_onefile.py -v 1.3.0

# Или скрипт спросит интерактивно
python build_scripts\build_folder.py
# >>> Введите версию приложения (например, 1.3.0):
```

---

## 📦 Что включается в сборку

Скрипты автоматически включают все необходимые пакеты:

- **PyQt5** - GUI framework
- **QFluentWidgets** - Fluent Design компоненты (транзитивно тянет qframelesswindow)
- **openpyxl** - Экспорт в Excel
- **speedtest-cli** - Движок тестирования скорости

**Qt плагины:**
- platforms, styles, iconengines, imageformats, platformthemes, printsupport

---

## 🔧 Процесс сборки

### Что происходит:

1. **Проверка файлов** - main.py, app.ico, version.py
2. **Определение компилятора** - MSVC или MinGW-w64
3. **Запуск Nuitka** - компиляция Python в C++
4. **Сборка exe** - создание исполняемого файла
5. **Упаковка ресурсов** - включение всех зависимостей

### Вывод скрипта:

```
============================================================
🚀 Сборка Speedtest NextGen (Standalone)
============================================================
✅ Файл приложения: main.py
✅ Иконка: app.ico
✅ Версия: 1.3.0

🔧 Компилятор: MSVC (latest)
🐍 Python: 3.13.0

📦 Включённые пакеты:
   - PyQt5 (GUI framework)
   - QFluentWidgets (Fluent Design)
   - openpyxl (Excel export)
   - speedtest-cli (Speed test engine)

⚙️  Запуск Nuitka...
============================================================
[... процесс компиляции ...]
============================================================
✅ Сборка завершена успешно!
📁 Результат: build/SpeedTestNextgen.dist/
============================================================
```

---

## 📁 Структура результата

### Standalone (папка):
```
build/
└── SpeedTestNextgen.dist/
    ├── SpeedTestNextgen.exe  ← Главный файл
    ├── Qt5Core.dll
    ├── Qt5Gui.dll
    ├── Qt5Widgets.dll
    ├── python313.dll
    └── ... (другие DLL и ресурсы)
```

### Onefile (один файл):
```
build/
└── SpeedTestNextgen.exe  ← Всё в одном файле
```

---

## ⚠️ Решение проблем

### Проблема 1: "Nuitka not found"

```bash
# РЕШЕНИЕ: Установить Nuitka
pip install nuitka
```

### Проблема 2: "MSVC not found" (Python 3.13+)

```bash
# РЕШЕНИЕ: Установить Visual Studio Build Tools
# 1. Скачать: https://visualstudio.microsoft.com/downloads/
# 2. Выбрать "Build Tools for Visual Studio"
# 3. Установить "Desktop development with C++"
```

### Проблема 3: "MinGW not found" (Python 3.12 и ниже)

```bash
# РЕШЕНИЕ: Установить MinGW-w64
# 1. Скачать: https://winlibs.com/
# 2. Распаковать в C:\mingw64
# 3. Добавить C:\mingw64\bin в PATH
```

### Проблема 4: Сборка падает с ошибкой

```bash
# РЕШЕНИЕ 1: Проверить, что все зависимости установлены
pip install -r requirements.txt

# РЕШЕНИЕ 2: Очистить кэш Nuitka
python -m nuitka --remove-output build

# РЕШЕНИЕ 3: Попробовать другой компилятор
# Отредактировать скрипт, изменить use_msvc на противоположное
```

### Проблема 5: Exe не запускается

```bash
# РЕШЕНИЕ: Проверить, что все DLL на месте (для standalone)
# Проверить антивирус - он мог заблокировать файл
# Запустить из командной строки, чтобы увидеть ошибку:
build\SpeedTestNextgen.exe
```

---

## 💡 Советы по сборке

1. **Для разработки** используйте `build_folder.py` - быстрее
2. **Для релиза** используйте `build_onefile.py` - удобнее
3. **Перед сборкой** убедитесь, что версия в `version.py` правильная
4. **Тестируйте** собранный exe перед распространением
5. **Антивирусы** могут ругаться на Nuitka-сборки - это нормально
6. **Размер** onefile будет ~100-150 MB - это нормально для PyQt5 приложений

---

## 🎓 Дополнительные опции Nuitka

Если нужно изменить параметры сборки, отредактируйте скрипты:

```python
# Добавить в cmd список:
"--show-progress",           # Показать прогресс сборки
"--show-memory",             # Показать использование памяти
"--remove-output",           # Удалить старую сборку
"--assume-yes-for-downloads", # Автоматически скачивать зависимости
"--disable-console",         # Отключить консоль (уже есть)
"--windows-uac-admin",       # Требовать права администратора
```

---

## 📚 Полезные ссылки

- [Nuitka Documentation](https://nuitka.net/doc/user-manual.html)
- [PyQt5 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [QFluentWidgets](https://qfluentwidgets.com/)
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
- [MinGW-w64](https://winlibs.com/)

---

**🎉 Готово! Теперь вы можете собирать приложение в exe файл!**
