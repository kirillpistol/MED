"""Read-only status panel for the MED collection history."""
import os
import sqlite3
from pathlib import Path

def collection_status(db_path=None):
    path = Path(db_path or os.getenv("MED_COLLECTION_DB", "med-collection.sqlite3"))
    if not path.is_file():
        return {"description": "журнал ещё не создан", "latest": []}
    try:
        with sqlite3.connect(path) as conn:
            entries = conn.execute("""SELECT executed_at,source,query,status,count,
                versions_added,error_type FROM collection_runs
                ORDER BY id DESC LIMIT 12""").fetchall()
    except sqlite3.Error:
        return {"description": "нет доступного журнала обновлений", "latest": []}
    cols = ("Время UTC", "Источник", "Запрос", "Результат", "Записей", "Новых версий", "Ошибка")
    return {"description": f"последних запусков: {len(entries)}",
            "latest": [dict(zip(cols, entry)) for entry in entries]}
