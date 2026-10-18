"""Independent MED public-research collection worker.

Run `python collector.py once` for an auditable cycle, or
`python collector.py serve` for periodic polling. Only public metadata;
no patient observations, no diagnosis decisions, and no GENESIS coupling.
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from clinical_trials import search_studies
from history import archive_public_studies
from research import search_publications

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "collection.json"
LOG_PATH_ENV = "MED_COLLECTION_DB"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    hours = config.get("schedule_hours")
    jobs = config.get("queries")
    if not isinstance(hours, (int, float)) or not 1 <= hours <= 168:
        raise ValueError("schedule_hours must be 1..168")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 20:
        raise ValueError("queries must contain 1..20 items")
    for job in jobs:
        if not isinstance(job, dict) or job.get("source") not in ("pubmed", "clinicaltrials"):
            raise ValueError("unknown source")
        term, limit = job.get("term"), job.get("limit")
        if not isinstance(term, str) or not 3 <= len(term) <= 120:
            raise ValueError("invalid term")
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("invalid limit")
    return config


def _log(result: dict, db_path: str | None) -> None:
    if not db_path:
        return
    connection = sqlite3.connect(db_path, timeout=10)
    try:
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("""CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executed_at TEXT NOT NULL,
            source TEXT NOT NULL,
            query TEXT NOT NULL,
            status TEXT NOT NULL,
            count INTEGER NOT NULL,
            versions_added INTEGER NOT NULL,
            error_type TEXT
        )""")
        connection.execute(
            """INSERT INTO collection_runs
               (executed_at, source, query, status, count, versions_added, error_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (result["executed_at"], result["source"], result["query"],
             result["status"], result["count"], result["versions_added"], result.get("error_type")))
        connection.commit()
    finally:
        connection.close()


def run_cycle(config: dict | None = None, *, db_path: str | None = None) -> list[dict]:
    config = config or _config()
    db_path = db_path if db_path is not None else os.getenv(LOG_PATH_ENV)
    results = []
    for job in config["queries"]:
        source, query, limit = job["source"], job["term"], job["limit"]
        row = {"executed_at": _now(), "source": source, "query": query,
               "status": "ok", "count": 0, "versions_added": 0}
        try:
            if source == "pubmed":
                data = search_publications(query, limit, force=True)
            elif source == "clinicaltrials":
                data = search_studies(query, limit, force=True)
                archived = archive_public_studies(data["records"])
                row["versions_added"] = archived["inserted_versions"]
            else:
                raise ValueError("unsupported source")
            row["count"] = data["count"]
        except Exception as exc:
            row["status"] = "error"
            row["error_type"] = type(exc).__name__
        results.append(row)
        _log(row, db_path)
        # Source requests are strictly sequential; avoid rapid repeated queries.
        if source == "pubmed":
            time.sleep(0.5)
    return results


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode not in ("once", "serve"):
        print("Usage: python collector.py [once|serve]", file=sys.stderr)
        return 2
    config = _config()
    while True:
        rows = run_cycle(config)
        print(json.dumps(rows, ensure_ascii=False), flush=True)
        if mode == "once":
            return 1 if any(row["status"] == "error" for row in rows) else 0
        time.sleep(config["schedule_hours"] * 3600)


if __name__ == "__main__":
    raise SystemExit(main())
