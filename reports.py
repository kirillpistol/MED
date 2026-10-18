"""Deterministic MED research evidence report, based on PUBLIC metadata only."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from analytics import study_analytics
from quality import archive_quality
from themes import summarize_themes

REPORT_SCHEMA = "med.research.report"

def generate_research_report(db_path: str | None = None) -> dict[str, Any]:
    result = study_analytics(db_path)
    calculation = {
        "source_id": result["source_id"],
        "scope": result["scope"],
        "archive_available": result["archive_available"],
        "studies": result["studies"],
        "archived_versions": result["archived_versions"],
        "changed_studies": result["changed_studies"],
        "status_counts": result["status_counts"],
        "phase_counts": result["phase_counts"],
        "changes": result["changes"],
    }
    quality = archive_quality(db_path)
    themes = summarize_themes(db_path)
    canonical = json.dumps({"analytics": calculation, "quality": quality, "themes": themes},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "report_type": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_checksum_sha256": digest,
        "data": calculation,
        "data_quality": quality,
        "research_themes": themes,
        "sections": ["Обзор", "Исследования", "Аналитика", "Качество данных", "Кровь", "Заболевания", "Повреждения", "Восстановление тканей", "Технологии улучшения функций организма", "Документы"],
        "methods": {
            "studies": "Count distinct NCT identifiers in local public-metadata archive.",
            "archived_versions": "Count archived versions identified by record checksum.",
            "changed_studies": "Count NCT identifiers with two or more archived versions.",
            "status_counts": "Latest archived status per NCT, not clinical outcome.",
            "phase_counts": "Latest archived distinct phase labels per NCT.",
            "changes": "Compare latest and immediately preceding archived versions.",
        },
        "limitations": [
            "Metadata checks cannot establish accuracy of published research.",
            "Local sample only; not all registered clinical trials.",
            "Record changes do not establish clinical effectiveness.",
            "No patient information and no diagnostic conclusions.",
        ],
        "primary_source": {
            "name": "ClinicalTrials.gov",
            "url": "https://clinicaltrials.gov/data-api/api",
            "record_url_pattern": "https://clinicaltrials.gov/study/{nct_id}",
        },
    }
