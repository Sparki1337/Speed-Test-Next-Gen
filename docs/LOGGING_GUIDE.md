# Руководство по логированию в Fluent Speedtest

## Обзор

Приложение использует профессиональную систему логирования с категориями, структурированными данными и асинхронной записью в файлы.

## Быстрый старт

### 1. Импорт логгера

```python
from core.logging_system import get_logger, LogCategory
```

### 2. Создание логгера для вашего модуля

Выберите подходящую категорию:

```python
# Для UI компонентов
logger = get_logger(LogCategory.UI)

# Для тестов скорости
logger = get_logger(LogCategory.TEST)

# Для сетевых операций
logger = get_logger(LogCategory.NETWORK)

# Для настроек
logger = get_logger(LogCategory.SETTINGS)

# Для истории
logger = get_logger(LogCategory.HISTORY)

# Для общих операций приложения
logger = get_logger(LogCategory.APP)

# Для ошибок
logger = get_logger(LogCategory.ERROR)
```

### 3. Использование логгера

#### Простое сообщение
```python
logger.info("Окно открыто")
logger.warning("Сервер недоступен")
logger.error("Не удалось загрузить данные")
logger.debug("Детали отладки")
```

#### Сообщение с структурированными данными
```python
logger.info("Открыта вкладка", data={
    'tab_name': 'История',
    'tab_index': 2
})

logger.info("Тест завершён", data={
    'ping': 25.5,
    'download_mbps': 100.5,
    'upload_mbps': 50.2,
    'server_id': 12345
})
```

#### Логирование исключений
```python
try:
    # код
    pass
except Exception as e:
    logger.error(f"Ошибка при выполнении операции: {e}", exc_info=True)
```

## Примеры для разных модулей

### UI компоненты (app_window.py, test_interface.py и т.д.)

```python
from core.logging_system import get_logger, LogCategory

class TestInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(LogCategory.UI)
        self.logger.info("Инициализация интерфейса тестирования")
    
    def start_test(self):
        self.logger.info("Пользователь нажал кнопку 'Тест'")
        # код теста
    
    def _on_result(self, result):
        self.logger.info("Получен результат теста", data={
            'ping': result.get('ping_ms'),
            'download': result.get('download_bps'),
            'upload': result.get('upload_bps')
        })
```

### Настройки (settings_interface.py)

```python
from core.logging_system import get_logger, LogCategory

class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(LogCategory.SETTINGS)
    
    def on_theme_changed(self, theme):
        self.logger.info(f"Тема изменена на {theme}", data={'theme': theme})
        self.settings.set('theme', theme)
    
    def on_units_changed(self, units):
        self.logger.info(f"Единицы измерения изменены на {units}", data={'units': units})
        self.settings.set('units', units)
```

### Тесты скорости (worker.py, speedtest_client.py)

```python
from core.logging_system import get_logger, LogCategory

class SpeedtestWorker(QObject):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(LogCategory.TEST)
    
    def run(self):
        self.logger.info("Начало теста скорости")
        
        try:
            self.logger.debug("Получение списка серверов")
            # код
            
            self.logger.info("Выбран лучший сервер", data={
                'server_id': server_id,
                'server_name': server_name,
                'distance': distance_km
            })
            
            self.logger.info("Тест загрузки (download)")
            # код
            
            self.logger.info("Тест отдачи (upload)")
            # код
            
            self.logger.info("Тест завершён успешно", data={
                'ping_ms': ping,
                'download_mbps': download / 1e6,
                'upload_mbps': upload / 1e6
            })
        except Exception as e:
            self.logger.error(f"Ошибка при тестировании: {e}", exc_info=True)
```

### Сетевой мониторинг (network_monitor.py)

```python
from core.logging_system import get_logger, LogCategory

class NetworkMonitor(QObject):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(LogCategory.NETWORK)
    
    def _check_connectivity(self):
        is_connected = # проверка
        
        if is_connected != self._was_connected:
            if is_connected:
                self.logger.info("Подключение к интернету восстановлено")
            else:
                self.logger.warning("Подключение к интернету потеряно")
            
            self._was_connected = is_connected
```

### История (history_interface.py, storage.py)

```python
from core.logging_system import get_logger, LogCategory

class HistoryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(LogCategory.HISTORY)
    
    def refresh(self):
        self.logger.info("Обновление истории тестов")
        results = load_results()
        self.logger.debug(f"Загружено {len(results)} записей")
    
    def export_to_csv(self, filepath):
        self.logger.info(f"Экспорт истории в CSV: {filepath}")
        try:
            # код экспорта
            self.logger.info("Экспорт завершён успешно", data={
                'filepath': filepath,
                'records_count': len(results)
            })
        except Exception as e:
            self.logger.error(f"Ошибка экспорта: {e}", exc_info=True)
    
    def clear_history(self):
        self.logger.warning("Пользователь очистил историю")
        # код очистки
        self.logger.info("История очищена")
```

## Рекомендации

### Что логировать:

✅ **Логировать:**
- Начало и завершение важных операций
- Изменения настроек
- Клики кнопок пользователя
- Открытие/закрытие окон и вкладок
- Результаты тестов
- Изменения состояния (подключение к сети и т.д.)
- Экспорт/импорт данных
- Ошибки и исключения

❌ **Не логировать:**
- Каждое движение мыши
- Каждый тик таймера
- Промежуточные состояния отрисовки UI
- Чувствительные данные (пароли, токены)

### Уровни логирования:

- **DEBUG**: Детальная отладочная информация (для разработки)
- **INFO**: Обычные информационные сообщения (по умолчанию)
- **WARNING**: Предупреждения о потенциальных проблемах
- **ERROR**: Ошибки, которые не останавливают приложение
- **CRITICAL**: Критические ошибки, приводящие к остановке

### Структурированные данные:

Всегда используйте параметр `data={}` для передачи дополнительной информации:

```python
# Плохо
logger.info(f"Результат: ping={ping}, download={download}, upload={upload}")

# Хорошо
logger.info("Результат теста получен", data={
    'ping_ms': ping,
    'download_bps': download,
    'upload_bps': upload,
    'server_id': server_id
})
```

Это позволяет легко парсить JSON логи и анализировать данные программно.

## Конфигурация

Пользователь может настроить логирование через UI:
- **Настройки → Уровень логирования**: DEBUG, INFO, WARNING, ERROR
- **Настройки → Буферизация логов**: 0 (без буферизации), 10, 50, 100 записей

Логи сохраняются в: `C:/Users/<User>/Documents/SpeedtestNextGen/logs/`

Файлы автоматически удаляются через 7 дней.

## Форматы

### В UI и консоли (человекочитаемый):
```
15:30:45 INFO     UI       Открыта вкладка: История
15:30:46 WARNING  NETWORK  Подключение к интернету потеряно
15:30:50 INFO     TEST     Тест завершён успешно
```

### В файлах (JSON):
```json
{"timestamp":"2025-10-04T15:30:45","level":"INFO","category":"UI","module":"history_interface","function":"refresh","line":45,"message":"Открыта вкладка: История","data":{"tab_name":"История","tab_index":2}}
{"timestamp":"2025-10-04T15:30:46","level":"WARNING","category":"NETWORK","module":"network_monitor","function":"_check_connectivity","line":78,"message":"Подключение к интернету потеряно"}
```

## Завершение работы

Система логирования автоматически завершает работу при закрытии приложения (в `main.py`):

```python
from core.logging_system import get_logging_system
get_logging_system().shutdown()
```

Это гарантирует, что все буферизованные записи будут сброшены в файл.
