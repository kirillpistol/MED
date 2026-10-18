"""Read-only inventory of proposed MED research data sources.

Proposed sources are never silently executed: no HTTP requests, third-party code
installation, or patient-data acquisition happens through this registry.
"""
from __future__ import annotations
import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "config" / "extended_sources.json"
VALID_CATEGORIES = {"russia", "regenerative", "bioprinting", "neuro"}

def source_catalog(path: Path = CATALOG_PATH, category: str | None = None) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    items = obj["sources"]
    if not isinstance(items, list):
        raise ValueError("source catalog must be a list")
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("source must be an object")
        if item["id"] in ids or item["category"] not in VALID_CATEGORIES:
            raise ValueError("duplicate source or unknown category")
        ids.add(item["id"])
        if item.get("fetch_enabled") is not False or item.get("status") != "candidate":
            raise ValueError("extended registry is inventory-only until individual review")
    if category is not None:
        if category not in VALID_CATEGORIES:
            raise ValueError("unknown source category")
        items = [item for item in items if item["category"] == category]
    return {"catalog": obj["schema"], "count": len(items), "sources": items,
            "all_sources_candidate": True, "network_requests_performed": 0}
