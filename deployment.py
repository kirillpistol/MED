"""MED deployment settings and topology checks.

Current deployment profile: single-host SQLite. Distributed storage is a
separate migration; this module does not claim it is implemented.
"""
from __future__ import annotations
import os
from pathlib import Path

DB_NAMES = {
    "history": ("MED_HISTORY_DB", "research.sqlite3"),
    "reports": ("MED_REPORTS_DB", "reports.sqlite3"),
    "collection": ("MED_COLLECTION_DB", "collection.sqlite3"),
    "discovery": ("MED_DISCOVERY_DB", "discovery.sqlite3"),
    "files": ("MED_FILES_DB", "files.sqlite3"),
}

def topology() -> dict:
    mode = os.getenv("MED_TOPOLOGY", "single-host")
    if mode != "single-host":
        raise ValueError("Only single-host topology is currently supported")
    paths = {}
    for key, (variable, default) in DB_NAMES.items():
        paths[key] = os.getenv(variable) or str(Path(os.getenv("MED_DATA_DIR", ".")).resolve() / default)
    return {"profile": mode, "storage": "sqlite-local", "database_paths": paths,
            "distributed_ready": False, "service_role": os.getenv("MED_SERVICE_ROLE", "api")}

def validate_storage() -> dict:
    state = topology()
    results = {}
    for name, configured in state["database_paths"].items():
        path = Path(configured)
        results[name] = {"parent_exists": path.parent.is_dir(),
                         "database_present": path.is_file()}
    return {"topology": state["profile"], "database_checks": results,
            "note": "Presence checks only; no writes, backups or migrations performed."}
