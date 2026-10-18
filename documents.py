"""Versioned public research reports for later GENESIS Services / Documents integration.

Local SQLite store; no patient files. Access over network must be mediated by L2.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def _db(path=None):
    return str(path or os.environ.get("MED_REPORTS_DB", "med-reports.sqlite3"))

def _connect(path=None):
    database = _db(path)
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        document_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
        created_at TEXT NOT NULL, sha256 TEXT NOT NULL,
        title TEXT NOT NULL, content_json TEXT NOT NULL)""")
    return conn

def publish_report(report: dict, path=None) -> dict:
    if report.get("report_type") != "med.research.report":
        raise ValueError("only public MED research reports can be published")
    content = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    document_id = "med-" + sha[:24]
    created = datetime.now(timezone.utc).isoformat()
    with _connect(path) as db:
        db.execute("INSERT OR IGNORE INTO reports VALUES (?,?,?,?,?,?)",
                   (document_id, report["report_type"], created, sha,
                    "Сводный исследовательский отчёт MED", content))
    return {"document_id": document_id, "title": "Сводный исследовательский отчёт MED",
            "kind": report["report_type"], "created_at": created, "sha256": sha,
            "format": "json", "origin": "MED-L3"}

def list_reports(path=None, limit: int = 50) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    if not Path(_db(path)).is_file():
        return {"schema": "med.documents.v1", "documents": []}
    with _connect(path) as db:
        rows = db.execute("SELECT document_id,kind,created_at,sha256,title FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return {"schema": "med.documents.v1", "documents": [
        {"document_id": r[0], "kind": r[1], "created_at": r[2],
         "sha256": r[3], "title": r[4], "format": "json", "origin": "MED-L3"} for r in rows]}

def get_report(document_id: str, path=None):
    import re
    if not re.fullmatch(r"med-[0-9a-f]{24}", document_id):
        return None
    if not Path(_db(path)).is_file():
        return None
    with _connect(path) as db:
        row = db.execute("SELECT content_json FROM reports WHERE document_id=?", (document_id,)).fetchone()
    return json.loads(row[0]) if row else None
