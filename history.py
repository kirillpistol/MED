"""SQLite archive for public study metadata only; no patient case data."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("MED_HISTORY_DB")

def archive_public_studies(records: list[dict]) -> dict:
    if not DB_PATH:
        return {"enabled": False, "inserted_versions": 0}
    # Explicitly archive ONLY externally retrieved, public ClinicalTrials.gov metadata.
    for row in records:
        if row.get("source_id") != "clinicaltrials" or not row.get("external_id", "").startswith("NCT"):
            raise ValueError("only public clinical-trial metadata can be archived")
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS study_versions (
            source_id TEXT NOT NULL,
            external_id TEXT NOT NULL,
            source_checksum_sha256 TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            record_json TEXT NOT NULL,
            PRIMARY KEY (source_id, external_id, source_checksum_sha256)
        )""")
        inserted = 0
        for row in records:
            cur = connection.execute(
                """INSERT OR IGNORE INTO study_versions
                (source_id, external_id, source_checksum_sha256, first_seen_at, record_json)
                VALUES (?, ?, ?, ?, ?)""",
                (row["source_id"], row["external_id"], row["source_checksum_sha256"],
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps(row, sort_keys=True, ensure_ascii=False)))
            inserted += cur.rowcount
        connection.commit()
        return {"enabled": True, "inserted_versions": inserted}
    finally:
        connection.close()

def study_history(nct_id: str) -> list[dict]:
    if not DB_PATH or not Path(DB_PATH).exists():
        return []
    connection = sqlite3.connect(DB_PATH, timeout=5)
    try:
        try:
            cursor = connection.execute(
                """SELECT source_checksum_sha256, first_seen_at, record_json
                   FROM study_versions WHERE source_id=? AND external_id=?
                   ORDER BY first_seen_at DESC LIMIT 25""",
                ("clinicaltrials", nct_id))
            return [{"checksum": r[0], "first_seen_at": r[1], "record": json.loads(r[2])}
                    for r in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
    finally:
        connection.close()
