# coding: utf-8
import json
from typing import List, Dict, Optional

# Данные должны храниться там же, где и настройки: Documents/SpeedtestNextGen/
try:
    from .settings import documents_dir, APP_FOLDER_NAME, get_settings
except ImportError:
    from core.settings import documents_dir, APP_FOLDER_NAME, get_settings  # type: ignore

# Папка данных внутри каталога приложения в Документах
APP_DATA_DIR = documents_dir() / APP_FOLDER_NAME
DATA_DIR = APP_DATA_DIR / 'data'
RESULTS_FILE = DATA_DIR / 'results.jsonl'

# Максимальное количество записей по умолчанию
DEFAULT_MAX_RECORDS = 1000

DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_result(result: Dict) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
    
    # Проверка и применение лимита записей
    _apply_records_limit()


def load_results(limit: Optional[int] = None) -> List[Dict]:
    if not RESULTS_FILE.exists():
        return []
    items: List[Dict] = []
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    if limit:
        return items[-limit:]
    return items


def clear_results() -> None:
    if RESULTS_FILE.exists():
        RESULTS_FILE.write_text('', encoding='utf-8')


def _apply_records_limit() -> None:
    """Применить лимит записей, удаляя старые результаты если превышен лимит."""
    try:
        settings = get_settings()
        max_records = int(settings.get('max_history_records', DEFAULT_MAX_RECORDS))
        
        if not RESULTS_FILE.exists():
            return
        
        # Загрузить все записи
        items: List[Dict] = []
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
        
        # Если превышен лимит, оставить только последние max_records записей
        if len(items) > max_records:
            items = items[-max_records:]
            
            # Перезаписать файл с ограниченным количеством записей
            with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
    except Exception:
        # Не прерываем работу приложения при ошибке лимита
        pass


def get_total_records_count() -> int:
    """Получить общее количество записей в истории."""
    if not RESULTS_FILE.exists():
        return 0
    
    count = 0
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    
    return count

