"""MED local document version registry.

Imports already obtained public source files from a local operator-controlled folder.
Network downloading is a separate, source-approved integration.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
EXTENSIONS = {".json", ".csv", ".xml"}

def register_file(path: Path, source_id: str, db_path: Path) -> dict:
    import re
    if not re.fullmatch(r"[a-z0-9_-]{2,60}", source_id):
        raise ValueError("invalid source ID")
    path = Path(path)
    if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
        raise ValueError("only existing JSON, CSV or XML files")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("file too large")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("file too large")
            digest.update(chunk)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS file_versions (
            source_id TEXT NOT NULL, sha256 TEXT NOT NULL,
            original_name TEXT NOT NULL, bytes INTEGER NOT NULL,
            registered_at TEXT NOT NULL, PRIMARY KEY(source_id, sha256))""")
        result = db.execute("""INSERT OR IGNORE INTO file_versions
            (source_id,sha256,original_name,bytes,registered_at) VALUES (?,?,?,?,?)""",
            (source_id, digest.hexdigest(), path.name, size,
             datetime.now(timezone.utc).isoformat()))
    return {"source_id": source_id, "sha256": digest.hexdigest(),
            "bytes": size, "new_version": result.rowcount == 1,
            "filename": path.name}

def file_inventory(db_path: Path) -> list[dict]:
    if not Path(db_path).exists():
        return []
    with sqlite3.connect(db_path) as db:
        rows = db.execute("SELECT source_id,sha256,original_name,bytes,registered_at FROM file_versions "
                          "ORDER BY registered_at DESC").fetchall()
    return [dict(zip(("source_id","sha256","filename","bytes","registered_at"), row)) for row in rows]
