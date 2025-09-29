# 🚀 Быстрый старт для разработчиков

## Первоначальная настройка

```bash
# Клонировать репозиторий
git clone <your-repo-url>
cd fluent_speedtest

# Установить зависимости
pip install -r requirements.txt

# Настроить Git для merge стратегии (один раз)
git config merge.ours.driver true
```

## Ежедневная разработка

### 1. Начать работу над новой функцией

```bash
# Переключиться на beta
git checkout beta
git pull origin beta

# Создать ветку для функции (опционально)
git checkout -b feature/my-feature

# Запустить приложение для тестирования
python -m fluent_speedtest
```

### 2. Внести изменения

```bash
# Редактировать код...
# Тестировать...

# Закоммитить изменения
git add .
git commit -m "feat: добавлена новая функция"
git push origin feature/my-feature
```

### 3. Слить в beta

```bash
git checkout beta
git merge feature/my-feature
git push origin beta
```

## Релиз в main

### Когда beta готова к релизу:

```bash
# 1. Переключиться на main
git checkout main
git pull origin main

# 2. Слить изменения из beta
git merge beta

# 3. Обновить статус на Stable
python set_version.py --status Stable

# 4. Закоммитить и запушить
git add version.py
git commit -m "release: v1.3.0 stable"
git push origin main

# 5. Создать тег
git tag -a v1.3.0 -m "Release v1.3.0"
git push origin main --tags

# 6. Вернуться в beta
git checkout beta
```

## Управление версией

```bash
# Посмотреть текущую версию
python set_version.py --show

# Обновить версию (например, для нового релиза)
python set_version.py --version 1.4.0

# Изменить статус
python set_version.py --status Beta
python set_version.py --status Stable
python set_version.py --status RC
```

## Полезные команды

```bash
# Запустить приложение
python -m fluent_speedtest
# или
python main.py

# Посмотреть различия между ветками
git diff main..beta

# Посмотреть статус Git
git status

# Посмотреть историю
git log --oneline --graph --all

# Отменить последний коммит (не запушенный)
git reset --soft HEAD~1
```

## Структура веток

```
main (Stable)
  └── v1.3.0 (tag)
  └── v1.2.0 (tag)

beta (Beta)
  └── feature/export-data
  └── feature/accent-colors
  └── feature/network-monitor
```

## Чеклист перед релизом

- [ ] Все тесты пройдены в beta
- [ ] Обновлён CHANGELOG.md
- [ ] Обновлена версия в version.py
- [ ] Обновлена документация (README.md)
- [ ] Проверена работа на чистой установке
- [ ] Создан merge request из beta в main
- [ ] После merge: установлен статус Stable
- [ ] Создан git tag с версией
- [ ] Опубликован релиз на GitHub

## Горячие клавиши Git

```bash
# Алиасы для удобства (добавить в ~/.gitconfig)
[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    lg = log --oneline --graph --all
    unstage = reset HEAD --
```

## Troubleshooting

### Конфликт при merge

```bash
# Если возник конфликт в version.py
git checkout main
git merge beta
# CONFLICT in version.py

# Разрешить конфликт вручную:
# 1. Открыть version.py
# 2. Оставить __status__ = "Stable" для main
# 3. Сохранить файл

git add version.py
git commit -m "merge: resolve conflict in version.py"
```

### Забыли обновить статус

```bash
# Если уже запушили в main с Beta статусом
git checkout main
python set_version.py --status Stable
git add version.py
git commit -m "fix: set status to Stable"
git push origin main
```

### Нужно откатить релиз

```bash
# Удалить тег локально и на сервере
git tag -d v1.3.0
git push origin :refs/tags/v1.3.0

# Откатить коммит
git revert HEAD
git push origin main
```
