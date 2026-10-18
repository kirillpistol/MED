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
        return search_studies(q, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Clinical trial registry temporarily unavailable")
