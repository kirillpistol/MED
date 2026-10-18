"""MED research themes. Public research discovery, not personal diagnosis."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import re
import sqlite3
from history import DB_PATH

THEMES = {
    "blood": {"name": "Кровь и гематология",
        "query": "hematology blood biomarkers",
        "keywords": ["blood", "hematolog", "anemia", "anaemia", "hemoglobin", "haemoglobin", "platelet", "leukemia", "leukaemia"]},
    "diseases": {"name": "Заболевания",
        "query": "disease diagnosis clinical research",
        "keywords": ["disease", "diagnos", "syndrome", "disorder", "diabetes", "oncolog", "cancer"]},
    "injuries": {"name": "Повреждения",
        "query": "traumatic injury rehabilitation",
        "keywords": ["injur", "trauma", "fracture", "wound", "burn", "rehabilitat"]},
    "tissue": {"name": "Восстановление тканей",
        "query": "tissue regeneration regenerative medicine",
        "keywords": ["tissue", "regenerat", "stem cell", "wound healing", "bioprint", "repair"]},
    "enhancement": {"name": "Технологии улучшения функций организма",
        "query": "prosthetics neural interface assistive technology",
        "keywords": ["prosthe", "neural interface", "assistive", "implant", "bionic", "augmentation", "exoskeleton"]},
}

def summarize_themes(db_path: str | None = None) -> dict:
    db = db_path if db_path is not None else DB_PATH
    rows = []
    if db and Path(db).exists():
        with sqlite3.connect(db, timeout=5) as connection:
            try:
                raw = connection.execute(
                    "SELECT external_id, record_json FROM study_versions "
                    "WHERE source_id='clinicaltrials' ORDER BY external_id, first_seen_at, rowid"
                ).fetchall()
            except sqlite3.OperationalError:
                raw = []
        # Preserve only the most recently archived version of each NCT.
        latest = {}
        for nct, payload in raw:
            try:
                record = json.loads(payload)
                if isinstance(record, dict):
                    latest[nct] = record
            except (ValueError, TypeError):
                continue
        rows = list(latest.values())
    summaries = {}
    for key, theme in THEMES.items():
        matches = []
        statuses = Counter()
        for record in rows:
            content = " ".join([str(record.get("title", "")),
                                " ".join(str(c) for c in record.get("conditions", [])),
                                " ".join(str(i.get("name", "")) for i in record.get("interventions", [])
                                         if isinstance(i, dict))]).casefold()
            if any(word.casefold() in content for word in theme["keywords"]):
                statuses[record.get("recruitment_status") or "UNKNOWN"] += 1
                matches.append({"nct": record.get("external_id"), "title": record.get("title"),
                                "url": record.get("url"), "status": record.get("recruitment_status")})
        summaries[key] = {
            "name": theme["name"], "query": theme["query"],
            "matched_studies": len(matches), "status_counts": dict(sorted(statuses.items())),
            "examples": matches[:20],
            "method": "Keyword matching of locally archived public registry metadata; overlap permitted.",
            "limitations": "Not medical evidence grading, population prevalence or treatment effectiveness.",
        }
    return {"archive_studies": len(rows), "themes": summaries,
            "method": "Non-exclusive research topic tagging; counts may overlap across themes."}
