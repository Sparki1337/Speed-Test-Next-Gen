# 🚀 Быстрый старт для разработчиков

## 📦 Первоначальная настройка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Sparki1337/Speed-Test-Next-Gen.git
cd fluent_speedtest

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить Git для merge стратегии (один раз)
git config merge.ours.driver true

# 4. Проверить, что всё работает
python -m fluent_speedtest
```

## 💻 Ежедневная разработка

### Шаг 1: Начать работу

```bash
# 1. Убедиться, что вы в ветке beta
git branch
# Должно показать: * beta

# 2. Если не в beta, переключиться
git checkout beta

# 3. Получить последние изменения
git pull origin beta

# 4. Проверить текущую версию
python set_version.py --show
# Должно быть: v1.3.0 | Beta
```

### Шаг 2: Внести изменения

```bash
# 1. Редактировать код в любом редакторе
# 2. Запустить и протестировать
python -m fluent_speedtest

# 3. Посмотреть, что изменилось
git status

# 4. Посмотреть детали изменений (опционально)
git diff
```

### Шаг 3: Закоммитить изменения

```bash
# 1. Добавить ВСЕ изменённые файлы
git add .

# 2. Проверить, что добавлено
git status
# Должно показать: "Changes to be committed:"

# 3. Создать коммит с описанием
git commit -m "feat: краткое описание изменений

- Детальное описание что сделано
- Ещё одна строка описания"

# 4. Запушить в удалённый репозиторий
git push origin beta
```

### ✅ Готово! Изменения в ветке beta

## 🚀 Релиз в main (когда beta готова)

### Полная последовательность действий:

```bash
# ШАГ 1: Убедиться, что вы в beta и всё работает
git checkout beta
python -m fluent_speedtest
# Протестировать все функции

# ШАГ 2: Собрать exe для тестирования
python build_scripts\build_folder.py
# Дождаться завершения (5-10 минут)

# ШАГ 3: Протестировать собранный exe
build\SpeedTestNextgen.dist\SpeedTestNextgen.exe
# Проверить, что всё работает в exe

# ШАГ 4: Если тесты прошли - собрать финальную версию
python build_scripts\build_onefile.py
# Дождаться завершения (10-15 минут)
# Результат: build/SpeedTestNextgen.exe

# ШАГ 5: Переключиться на main
git checkout main
git pull origin main

# ШАГ 6: Слить изменения из beta
git merge beta
# Если появятся конфликты - разрешите их вручную

# ШАГ 7: Обновить статус на Stable
python set_version.py --status Stable
# Должно показать: v1.3.0 | Stable

# ШАГ 8: Проверить, что всё работает
python -m fluent_speedtest
# Запустите приложение и убедитесь, что в заголовке "Stable"

# ШАГ 9: Закоммитить изменение статуса
git add version.py
git commit -m "release: v1.3.1 stable"

# ШАГ 10: Запушить в main
git push origin main

# ШАГ 11: Создать тег для релиза
git tag -a v1.3.1 -m "Release v1.3.1"
git push origin main --tags

# ШАГ 12: Создать GitHub Release  
# 1. Перейти на GitHub в раздел Releases
# 2. Нажать "Create a new release"
# 3. Выбрать тег v1.3.1
# 4. Прикрепить файл build/SpeedTestNextgen.exe
# 5. Описать изменения из CHANGELOG.md
# 6. Опубликовать релиз

# ШАГ 13: Вернуться в beta для дальнейшей разработки
git checkout beta
```

### ✅ Готово! Релиз опубликован в main и на GitHub

## 🔧 Управление версией

### Посмотреть текущую версию
```bash
python set_version.py --show
```
**Вывод:**
```
📦 Текущая версия: v1.3.0 | Beta
   Номер версии: 1.3.0
   Статус: Beta
```

### Обновить версию (для нового релиза)
```bash
# Обновить только номер версии
python set_version.py --version 1.4.0

# Обновить версию И статус одновременно
python set_version.py --version 1.4.0 --status Beta
```

### Изменить только статус
```bash
# Для ветки beta
python set_version.py --status Beta

# Для ветки main
python set_version.py --status Stable

# Для релиз-кандидата
python set_version.py --status RC
```

## 📚 Полезные команды

### Работа с приложением
```bash
# Запустить приложение (рекомендуется)
python -m fluent_speedtest

# Альтернативный способ
python main.py

# Проверить версию
python set_version.py --show
```

### Работа с Git
```bash
# Посмотреть текущую ветку и статус
git status

# Посмотреть список веток
git branch

# Посмотреть различия между ветками
git diff main..beta

# Посмотреть историю коммитов (красиво)
git log --oneline --graph --all

# Посмотреть последние 5 коммитов
git log --oneline -5

# Посмотреть изменения в конкретном файле
git diff version.py
```

### Отмена действий
```bash
# Отменить последний коммит (НЕ запушенный)
git reset --soft HEAD~1

# Убрать файл из staging (после git add)
git restore --staged filename.py

# Отменить изменения в файле (вернуть как было)
git restore filename.py
```

## 🌳 Структура веток

```
main (Stable) ← Только стабильные релизы
  ├── v1.3.0 (tag)
  ├── v1.2.0 (tag)
  └── v1.1.0 (tag)

beta (Beta) ← Вся разработка здесь
  ├── Новые функции
  ├── Исправления багов
  └── Тестирование
```

**Правило:** Всегда работаем в `beta`, релизим в `main`

## 🔨 Сборка приложения

### Когда собирать?

Сборку делаем **перед релизом в main**:
- ✅ Все функции протестированы
- ✅ Версия обновлена в `version.py`
- ✅ Готовы к публикации

### Как собрать?

```bash
# 1. Сборка для тестирования (быстрая)
python build_scripts\build_folder.py
# Результат: build/SpeedTestNextgen.dist/SpeedTestNextgen.exe
# Время: 5-10 минут

# 2. Протестировать exe
build\SpeedTestNextgen.dist\SpeedTestNextgen.exe

# 3. Сборка для релиза (один файл)
python build_scripts\build_onefile.py
# Результат: build/SpeedTestNextgen.exe
# Время: 10-15 минут
```

### Что проверить в собранном exe?

- [ ] Приложение запускается
- [ ] Все функции работают (тест, серверы, история, настройки)
- [ ] Экспорт в CSV/Excel работает
- [ ] Акцентные цвета применяются
- [ ] Индикатор интернета работает
- [ ] Версия отображается правильно в заголовке

📖 **Подробная инструкция**: см. `build_scripts/README.md`

---

## ✅ Чеклист перед релизом в main

Перед тем как делать `git merge beta` в main, проверьте:

- [ ] **Приложение запускается** без ошибок в beta
- [ ] **Все функции работают** корректно
- [ ] **Собран и протестирован exe** (см. раздел "Сборка приложения")
- [ ] **Обновлён CHANGELOG.md** с описанием изменений
- [ ] **Обновлена версия** в `version.py` (если нужна новая версия)
- [ ] **Обновлена документация** (README.md, если нужно)
- [ ] **Протестировано** на чистой установке
- [ ] **Нет незакоммиченных изменений** (`git status` чистый)

После merge в main:

- [ ] **Установлен статус Stable** (`python set_version.py --status Stable`)
- [ ] **Создан git tag** с версией (`git tag -a v1.3.0`)
- [ ] **Запушены изменения** и теги в GitHub
- [ ] **Создан GitHub Release** с прикреплённым exe файлом

## ⚠️ Решение проблем

### Проблема 1: Конфликт при merge

**Ситуация:** При `git merge beta` возник конфликт в `version.py`

```bash
git checkout main
git merge beta
# >>> CONFLICT in version.py <<<

# РЕШЕНИЕ:
# 1. Открыть version.py в редакторе
# 2. Найти строки с <<<<<<< HEAD и >>>>>>> beta
# 3. Оставить __status__ = "Stable" для main
# 4. Удалить маркеры конфликта
# 5. Сохранить файл

git add version.py
git commit -m "merge: resolve conflict in version.py"
git push origin main
```

### Проблема 2: Забыли обновить статус

**Ситуация:** Запушили в main, но статус остался "Beta"

```bash
# РЕШЕНИЕ:
git checkout main
python set_version.py --status Stable
git add version.py
git commit -m "fix: set status to Stable"
git push origin main
```

### Проблема 3: Ошибка при push

**Ситуация:** `git push` выдаёт ошибку

```bash
# РЕШЕНИЕ 1: Сначала получить изменения
git pull origin beta
# Разрешить конфликты если есть
git push origin beta

# РЕШЕНИЕ 2: Если нужно перезаписать (ОСТОРОЖНО!)
git push origin beta --force
```

### Проблема 4: Нужно откатить коммит

**Ситуация:** Закоммитили что-то неправильно (НЕ запушили)

```bash
# РЕШЕНИЕ: Отменить последний коммит
git reset --soft HEAD~1
# Файлы останутся изменёнными, можно исправить и закоммитить снова
```

### Проблема 5: Нужно откатить релиз

**Ситуация:** Релиз в main оказался с багами

```bash
# РЕШЕНИЕ:
# 1. Удалить тег
git tag -d v1.3.0
git push origin :refs/tags/v1.3.0

# 2. Откатить коммит
git checkout main
git revert HEAD
git push origin main

# 3. Исправить баги в beta и сделать новый релиз
```

### Проблема 6: Не знаю, в какой ветке я нахожусь

```bash
# РЕШЕНИЕ: Посмотреть текущую ветку
git branch
# Звёздочка (*) покажет текущую ветку

# Или посмотреть статус
git status
# Первая строка: "On branch beta"
```

## 💡 Полезные советы

1. **Всегда проверяйте `git status`** перед коммитом
2. **Используйте `git diff`** чтобы увидеть что изменилось
3. **Коммитьте часто** - лучше много маленьких коммитов, чем один большой
4. **Пишите понятные сообщения** в коммитах
5. **Тестируйте перед push** - запустите приложение
6. **Не бойтесь экспериментировать** в beta - для этого она и нужна!

## 🎓 Шпаргалка команд

```bash
# === ЧАСТЫЕ КОМАНДЫ ===
git status                    # Что изменилось?
git add .                     # Добавить всё
git commit -m "сообщение"     # Закоммитить
git push origin beta          # Запушить в beta
python set_version.py --show  # Какая версия?

# === ПЕРЕКЛЮЧЕНИЕ ВЕТОК ===
git checkout beta             # Перейти в beta
git checkout main             # Перейти в main
git branch                    # Список веток

# === ПРОСМОТР ИЗМЕНЕНИЙ ===
git diff                      # Что изменилось?
git log --oneline -5          # Последние 5 коммитов
git diff main..beta           # Разница между ветками

# === ОТМЕНА ДЕЙСТВИЙ ===
git restore filename.py       # Отменить изменения в файле
git reset --soft HEAD~1       # Отменить последний коммит
git restore --staged file.py  # Убрать из staging
```

---

**🎉 Готово! Теперь у вас есть полное руководство по работе с проектом!**

Если что-то непонятно - смотрите `GIT_WORKFLOW.md` для более детальных инструкций.
