# coding: utf-8
import json
from typing import List, Dict, Optional

# Данные должны храниться там же, где и настройки: Documents/SpeedtestNextGen/
try:
    from .settings import documents_dir, APP_FOLDER_NAME
except ImportError:
    from core.settings import documents_dir, APP_FOLDER_NAME  # type: ignore

# Папка данных внутри каталога приложения в Документах
APP_DATA_DIR = documents_dir() / APP_FOLDER_NAME
DATA_DIR = APP_DATA_DIR / 'data'
RESULTS_FILE = DATA_DIR / 'results.jsonl'

DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_result(result: Dict) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')


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

