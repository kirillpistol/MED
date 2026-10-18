"""Quality checks for publicly archived MED study records.

This checks metadata completeness and traceability, not scientific validity.
"""
from __future__ import annotations
import json
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from history import DB_PATH

SHA256 = re.compile(r"^[0-9a-f]{64}$")
NCT = re.compile(r"^NCT[0-9]{8}$")

def validate_record(record: dict) -> dict:
    issues = []
    nct = str(record.get("external_id") or "")
    if not NCT.fullmatch(nct):
        issues.append("invalid_nct")
    if record.get("source_id") != "clinicaltrials":
        issues.append("unexpected_source")
    if record.get("url") != "https://clinicaltrials.gov/study/" + nct:
        issues.append("invalid_source_url")
    if not str(record.get("title") or "").strip():
        issues.append("missing_title")
    if not str(record.get("recruitment_status") or "").strip():
        issues.append("missing_status")
    checksum = str(record.get("source_checksum_sha256") or "")
    if not SHA256.fullmatch(checksum):
        issues.append("invalid_checksum_format")
    updated = str(record.get("last_update_posted") or "")
    if not updated:
        issues.append("missing_update_date")
    else:
        try:
            if date.fromisoformat(updated) > datetime.now(timezone.utc).date():
                issues.append("future_update_date")
        except ValueError:
            issues.append("invalid_update_date")
    return {"external_id": nct, "passed": not issues, "issues": issues}

def archive_quality(db_path: str | None = None) -> dict:
    db = db_path if db_path is not None else DB_PATH
    result = {"source_id": "clinicaltrials", "archive_available": False,
              "checked": 0, "passed": 0, "failed": 0,
              "issue_counts": {}, "records_with_issues": [],
              "method": "Metadata completeness, identity, date and provenance checks; not clinical quality."}
    if not db or not Path(db).exists():
        return result
    with sqlite3.connect(db, timeout=5) as conn:
        try:
            rows = conn.execute(
                "SELECT external_id, source_checksum_sha256, record_json FROM study_versions "
                "WHERE source_id='clinicaltrials' ORDER BY external_id, rowid"
            ).fetchall()
        except sqlite3.OperationalError:
            return {**result, "archive_available": True}
    issues = Counter()
    bad = []
    passed = 0
    for external_id, checksum, raw in rows:
        try:
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("not an object")
            validation = validate_record(record)
            if external_id != record.get("external_id") or checksum != record.get("source_checksum_sha256"):
                validation["issues"].append("archive_identity_mismatch")
        except (ValueError, TypeError):
            validation = {"external_id": external_id, "passed": False, "issues": ["malformed_record_json"]}
        if validation["issues"]:
            issues.update(validation["issues"])
            if len(bad) < 100:
                bad.append({"external_id": external_id, "issues": sorted(set(validation["issues"]))})
        else:
            passed += 1
    return {**result, "archive_available": True, "checked": len(rows), "passed": passed,
            "failed": len(rows)-passed, "issue_counts": dict(sorted(issues.items())),
            "records_with_issues": bad}
