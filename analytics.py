"""MED Analytics: deterministic summaries of archived PUBLIC study metadata.

Counts reflect the bounded locally collected sample, not population prevalence
or clinical efficacy. No patient records or diagnostic probabilities.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path

from history import DB_PATH


def study_analytics(db_path: str | None = None) -> dict:
    db = db_path if db_path is not None else os.getenv("MED_HISTORY_DB", DB_PATH)
    generated = datetime.now(timezone.utc).isoformat()
    empty = {"generated_at": generated, "source_id": "clinicaltrials",
             "studies": 0, "archived_versions": 0, "changed_studies": 0,
             "status_counts": {}, "phase_counts": {},
             "changes": [], "scope": "locally archived public registry sample",
             "note": "Descriptive study metadata only; not clinical effectiveness or diagnosis."}
    if not db or not Path(db).exists():
        return {**empty, "archive_available": False}
    connection = sqlite3.connect(db, timeout=5)
    try:
        try:
            records = connection.execute(
                """SELECT external_id, source_checksum_sha256, first_seen_at, record_json
                   FROM study_versions WHERE source_id='clinicaltrials'
                   ORDER BY external_id, first_seen_at, rowid""").fetchall()
        except sqlite3.OperationalError:
            return {**empty, "archive_available": True}
    finally:
        connection.close()
    by_id = defaultdict(list)
    for external_id, checksum, first_seen, raw in records:
        try:
            item = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        by_id[external_id].append((checksum, first_seen, item))
    status_counts, phases = Counter(), Counter()
    changes = []
    for nct, history in sorted(by_id.items()):
        latest = history[-1][2]
        status_counts[latest.get("recruitment_status") or "UNKNOWN"] += 1
        for phase in set(latest.get("phases") or []):
            phases[phase] += 1
        if len(history) > 1:
            prior = history[-2][2]
            changes.append({
                "external_id": nct,
                "url": latest.get("url", ""),
                "previous_checksum": history[-2][0],
                "current_checksum": history[-1][0],
                "previous_recruitment_status": prior.get("recruitment_status"),
                "current_recruitment_status": latest.get("recruitment_status"),
                "recruitment_status_changed":
                    prior.get("recruitment_status") != latest.get("recruitment_status"),
                "version_count": len(history),
            })
    return {**empty, "archive_available": True, "studies": len(by_id),
            "archived_versions": sum(map(len, by_id.values())),
            "changed_studies": len(changes),
            "status_counts": dict(sorted(status_counts.items())),
            "phase_counts": dict(sorted(phases.items())),
            "changes": changes[:100]}
