# Git Workflow для управления версиями Beta и Main

## 🎯 Проблема
При merge из ветки `beta` в `main` нужно, чтобы версия оставалась разной:
- **beta**: `v1.3.0 | Beta`
- **main**: `v1.3.0 | Stable`

## ✅ Решение: Файл version.py

### Структура
Вся информация о версии теперь в файле `version.py`:
```python
__version__ = "1.3.0"
__status__ = "Beta"  # или "Stable" в main
```

---

## 🔨 Когда собирать exe?

Сборку приложения нужно делать **перед релизом в main**:

1. ✅ Все функции протестированы в beta
2. ✅ Версия обновлена в `version.py`
3. ✅ Код закоммичен и запушен в beta
4. ✅ **Собран и протестирован exe файл**
5. ✅ Готовы к публикации релиза

**Команды для сборки:**
```bash
# Быстрая сборка для тестирования (5-10 минут)
python build_scripts\build_folder.py

# Финальная сборка для релиза (10-15 минут)
python build_scripts\build_onefile.py
```

📖 Подробная инструкция: `build_scripts/README.md`

---

## 📋 Workflow для работы с ветками

### 1. Работа в ветке Beta

```bash
# Переключиться на beta
git checkout beta

# Внести изменения в код
# Обновить version.py:
# __version__ = "1.3.0"
# __status__ = "Beta"

git add .
git commit -m "feat: добавлены новые функции"
git push origin beta
```

### 2. Подготовка к релизу в Main

**ВАЖНО:** Перед релизом нужно собрать exe файл!

#### Шаг 2.1: Сборка приложения (в beta)

```bash
# Убедиться, что вы в beta
git checkout beta

# Собрать exe для тестирования
python build_scripts\build_folder.py
# Дождаться завершения (5-10 минут)

# Протестировать собранный exe
build\SpeedTestNextgen.dist\SpeedTestNextgen.exe

# Если всё работает - собрать финальную версию
python build_scripts\build_onefile.py
# Дождаться завершения (10-15 минут)
# Результат: build/SpeedTestNextgen.exe
```

#### Шаг 2.2: Релиз в main (ручное управление - рекомендуется)

```bash
# 1. Переключиться на main
git checkout main

# 2. Слить изменения из beta
git merge beta

# 3. Если есть конфликт в version.py, разрешить его:
#    Оставить __status__ = "Stable" в main

# 4. Обновить version.py вручную:
python set_version.py --status Stable

# 5. Закоммитить
git add version.py
git commit -m "release: v1.3.0 stable"
git push origin main

# 6. Создать тег
git tag -a v1.3.0 -m "Release v1.3.0"
git push origin main --tags

# 7. Создать GitHub Release и прикрепить build/SpeedTestNextgen.exe
```

#### Вариант Б: Автоматическая стратегия слияния

```bash
# Настроить Git один раз (уже настроено через .gitattributes):
git config merge.ours.driver true

# Теперь при merge version.py всегда будет брать версию из текущей ветки
git checkout main
git merge beta
# version.py останется с __status__ = "Stable"

git push origin main
```

---

## 🔧 Настройка веток

### Настройка ветки Beta
```bash
git checkout beta

# Отредактировать version.py:
# __status__ = "Beta"

git add version.py
git commit -m "chore: установить статус Beta"
git push origin beta
```

### Настройка ветки Main
```bash
git checkout main

# Отредактировать version.py:
# __status__ = "Stable"

git add version.py
git commit -m "chore: установить статус Stable"
git push origin main
```

---

## 📝 Правила работы

### ✅ DO (Делать):
1. **Всегда разрабатывать в beta**
2. **Обновлять `__version__` в обеих ветках одинаково**
3. **Держать `__status__` разным**: Beta в beta, Stable в main
4. **Тестировать в beta перед merge в main**
5. **Создавать теги после релиза в main**: `git tag v1.3.0`

### ❌ DON'T (Не делать):
1. **Не коммитить напрямую в main** (только через merge из beta)
2. **Не забывать обновлять version.py** перед релизом
3. **Не мержить в main без тестирования в beta**

---

## 🚀 Пример полного цикла релиза

```bash
# 1. Разработка в beta
git checkout beta
# ... делаем изменения ...
# Обновляем version.py: __version__ = "1.4.0", __status__ = "Beta"
git add .
git commit -m "feat: новая функция"
git push origin beta

# 2. Тестирование в beta
# ... тестируем приложение ...

# 3. Релиз в main
git checkout main
git merge beta

# 4. Обновить статус на Stable (если нужно)
# Отредактировать version.py: __status__ = "Stable"
git add version.py
git commit -m "release: v1.4.0 stable"

# 5. Создать тег
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin main --tags

# 6. Вернуться в beta для дальнейшей разработки
git checkout beta
```

---

## 🔍 Проверка текущей версии

```bash
# Посмотреть версию в beta
git checkout beta
cat version.py | grep __status__
# Должно быть: __status__ = "Beta"

# Посмотреть версию в main
git checkout main
cat version.py | grep __status__
# Должно быть: __status__ = "Stable"
```

---

## 💡 Дополнительные советы

### Автоматизация через Git Hooks

Создать `.git/hooks/post-checkout`:
```bash
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$BRANCH" = "main" ]; then
    # Автоматически установить Stable в main
    sed -i 's/__status__ = "Beta"/__status__ = "Stable"/g' version.py
elif [ "$BRANCH" = "beta" ]; then
    # Автоматически установить Beta в beta
    sed -i 's/__status__ = "Stable"/__status__ = "Beta"/g' version.py
fi
```

### Использование environment variables

Можно также использовать переменные окружения:
```python
# version.py
import os
__version__ = "1.3.0"
__status__ = os.getenv("APP_STATUS", "Beta")
```

Тогда при сборке:
```bash
# Для beta
python main.py

# Для stable
APP_STATUS=Stable python main.py
```

---

## 📚 Полезные команды Git

```bash
# Посмотреть различия между ветками
git diff main..beta version.py

# Отменить merge (если что-то пошло не так)
git merge --abort

# Посмотреть историю коммитов
git log --oneline --graph --all

# Создать новую ветку для фичи
git checkout -b feature/new-feature beta

# Удалить локальную ветку
git branch -d feature/old-feature

# Обновить beta из main (если нужно синхронизировать)
git checkout beta
git merge main
```

---

## 🎯 Итог

Теперь у вас есть:
1. ✅ Файл `version.py` для управления версией
2. ✅ Файл `.gitattributes` для стратегии слияния
3. ✅ Чёткий workflow для работы с ветками
4. ✅ Автоматическое управление статусом Beta/Stable

**Главное правило:** Всегда проверяйте `version.py` после merge!
