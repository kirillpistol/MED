"""Stable internal status contract for MED L3 integrations."""
from __future__ import annotations
from datetime import datetime, timezone
import os
from pathlib import Path
from analytics import study_analytics
from quality import archive_quality
from discovery import discovery_inventory
from collector_status import collection_status

CONTRACT = "med.integration.status"
VERSION = "1"

def integration_status() -> dict:
    issues = []
    try:
        archive = study_analytics()
        research = {"available": archive["archive_available"], "studies": archive["studies"],
                    "archived_versions": archive["archived_versions"]}
    except Exception:
        issues.append("research_archive")
        research = {"available": False, "studies": 0, "archived_versions": 0}
    try:
        quality = archive_quality()
        verification = {"available": quality["archive_available"], "checked": quality["checked"],
                        "failed": quality["failed"]}
    except Exception:
        issues.append("metadata_quality")
        verification = {"available": False, "checked": 0, "failed": 0}
    try:
        candidates = discovery_inventory(limit=1)
        discovery = {"storage_available": Path(os.getenv("MED_DISCOVERY_DB",
                    "med-discovery.sqlite3")).is_file(), "has_candidates": bool(candidates)}
    except Exception:
        issues.append("discovery_storage")
        discovery = {"storage_available": False, "has_candidates": False}
    try:
        status = collection_status()
        collector = {"recent_runs": len(status["latest"]), "journal": status["description"]}
    except Exception:
        issues.append("collector_journal")
        collector = {"recent_runs": 0, "journal": "unavailable"}
    return {
        "contract": CONTRACT, "contract_version": VERSION,
        "service": "med", "layer": "L3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state": "degraded" if issues else "ready",
        "components": {"research_archive": research, "quality": verification,
                       "discovery": discovery, "collector": collector},
        "issues": issues,
        "integration": {"protocol": "http-json", "scope": "internal",
                        "clinical_validation": False},
    }
