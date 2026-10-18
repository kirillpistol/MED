"""MED: standalone experimental diagnostic hypothesis engine.
Synthetic scenarios only. Not validated for clinical use, no patient storage.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from research import search_publications
from clinical_trials import search_studies
from history import archive_public_studies, study_history
from analytics import study_analytics
from reports import generate_research_report
from quality import archive_quality
from integration import integration_status
from documents import publish_report, list_reports, get_report
import re
import sqlite3

app = FastAPI(title="MED", docs_url=None, redoc_url=None)

# These are illustrative *syndrome labels*, not validated medical diagnoses.
CATALOG = {
    "respiratory_pattern": {"fever": 2, "cough": 2, "dyspnea": 2},
    "gastrointestinal_pattern": {"abdominal_pain": 2, "nausea": 2, "diarrhea": 2},
    "neurologic_pattern": {"headache": 2, "dizziness": 2, "confusion": 3},
}
ALLOWED = sorted({feature for weights in CATALOG.values() for feature in weights})
MODEL_VERSION = "med-pattern-demo"


class Observation(BaseModel):
    code: Literal[
        "fever", "cough", "dyspnea", "abdominal_pain", "nausea",
        "diarrhea", "headache", "dizziness", "confusion"
    ]
    present: bool


class CaseRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    synthetic: Literal[True]
    observations: list[Observation] = Field(min_length=1, max_length=9)


def calculate(case: CaseRequest) -> dict:
    features = {}
    for item in case.observations:
        if item.code in features:
            raise ValueError("duplicate observation: " + item.code)
        features[item.code] = item.present
    candidates = []
    for label, weights in CATALOG.items():
        matched = sorted(code for code in weights if features.get(code) is True)
        contradicted = sorted(code for code in weights if features.get(code) is False)
        total = sum(weights.values())
        matched_weight = sum(weights[c] for c in matched)
        score = round(matched_weight / total, 4)
        candidates.append({
            "pattern": label, "similarity_score": score,
            "matched": matched, "contradicted": contradicted,
            "method": "weighted_rule_overlap; not probability",
        })
    candidates.sort(key=lambda x: (-x["similarity_score"], x["pattern"]))
    payload = {"case_id": case.case_id, "observations": features, "model_version": MODEL_VERSION}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {
        "case_id": case.case_id, "model_version": MODEL_VERSION,
        "input_sha256": digest,
        "candidates": candidates,
        "warnings": [
            "Research prototype only: synthetic inputs, non-validated heuristic.",
            "Similarity scores are not diagnostic probabilities.",
            "Do not use for medical diagnosis, triage, or treatment decisions.",
        ],
        "trace": {"input_feature_codes": sorted(features), "algorithm": "weighted_rule_overlap",
                  "catalog_version": MODEL_VERSION},
    }


@app.get("/healthz")
def health():
    return {"status": "ok", "service": "med"}


@app.post("/analyze")
def analyze(case: CaseRequest):
    try:
        return calculate(case)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/report")
def report(case: CaseRequest):
    result = analyze(case)
    return {"report_type": "med-synthetic-analysis", "created_at": datetime.now(timezone.utc).isoformat(),
            "report": result}

@app.get("/research/publications")
def publications(q: str = Query(min_length=3, max_length=120),
                 limit: int = Query(default=5, ge=1, le=10)):
    """Read-only public PubMed bibliographic discovery; no patient information."""
    try:
        return search_publications(q, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        # Do not expose upstream URLs or diagnostic details through the public API.
        raise HTTPException(status_code=503, detail="Research provider temporarily unavailable")

@app.get("/research/studies")
def clinical_studies(q: str = Query(min_length=3, max_length=120),
                     limit: int = Query(default=5, ge=1, le=10)):
    """Normalized public ClinicalTrials.gov registry metadata."""
    try:
        results = search_studies(q, limit)
        try:
            results["archive"] = archive_public_studies(results["records"])
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            results["archive"] = {"enabled": True, "error": "archive temporarily unavailable"}
        return results
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Clinical trial registry temporarily unavailable")

@app.get("/research/studies/{nct_id}/history")
def clinical_study_history(nct_id: str):
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id):
        raise HTTPException(status_code=422, detail="Invalid NCT identifier")
    return {"source_id": "clinicaltrials", "external_id": nct_id,
            "versions": study_history(nct_id)}

@app.get("/analytics/studies")
def public_study_analytics():
    """Descriptive counts and version changes from MED's local public-study archive."""
    try:
        return study_analytics()
    except Exception:
        raise HTTPException(status_code=503, detail="Study analytics temporarily unavailable")

@app.get("/reports/research")
def research_report():
    """Method-documented report on local public-study metadata."""
    try:
        return generate_research_report()
    except Exception:
        raise HTTPException(status_code=503, detail="Research report temporarily unavailable")

@app.get("/quality/studies")
def study_source_quality():
    """Completeness and provenance checks for locally archived public metadata."""
    try:
        return archive_quality()
    except Exception:
        raise HTTPException(status_code=503, detail="Quality check temporarily unavailable")

@app.get("/integration/status")
def med_integration_status():
    """Versioned, non-patient MED L3 status for future CORE/L2 orchestration."""
    return integration_status()

@app.post("/documents/research", status_code=201)
def create_research_document():
    """Persist a public, aggregate research report for later L2 consumption."""
    try:
        return publish_report(generate_research_report())
    except Exception:
        raise HTTPException(status_code=503, detail="Report publishing unavailable")

@app.get("/documents")
def documents_index(limit: int = Query(default=50, ge=1, le=100)):
    return list_reports(limit=limit)

@app.get("/documents/{document_id}")
def document_details(document_id: str):
    result = get_report(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
