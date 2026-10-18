"""Read-only ClinicalTrials.gov metadata adapter, with local normalization and bounded cache."""
from __future__ import annotations
import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL = "https://clinicaltrials.gov/api/v2/studies"
_lock = threading.Lock()
_cache = {}
TTL_SECONDS = 600

def _fetch(params: dict) -> dict:
    req = Request(URL + "?" + urlencode(params), headers={
        "Accept": "application/json", "User-Agent": "MED-PublicResearch/1.0"})
    with urlopen(req, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError("ClinicalTrials.gov unavailable")
        return json.load(response)

def normalize_study(study: dict, retrieved_at: str) -> dict:
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    conditions = protocol.get("conditionsModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    nct = identification.get("nctId", "")
    if not re.fullmatch(r"NCT[0-9]{8}", nct):
        raise ValueError("invalid NCT identifier")
    raw_bytes = json.dumps(study, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {
        "source_id": "clinicaltrials",
        "external_id": nct,
        "url": "https://clinicaltrials.gov/study/" + nct,
        "title": identification.get("briefTitle", ""),
        "official_title": identification.get("officialTitle", ""),
        "recruitment_status": status.get("overallStatus", ""),
        "last_update_posted": status.get("lastUpdatePostDateStruct", {}).get("date", ""),
        "study_type": design.get("studyType", ""),
        "phases": design.get("phases", []),
        "conditions": conditions.get("conditions", []),
        "interventions": [
            {"type": it.get("type", ""), "name": it.get("name", "")}
            for it in arms.get("interventions", []) if isinstance(it, dict)
        ][:30],
        "retrieved_at": retrieved_at,
        "source_checksum_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "adapter": "clinicaltrials-api-v2",
    }

def search_studies(term: str, limit: int = 5, *, force: bool = False) -> dict:
    term = term.strip()
    if not (3 <= len(term) <= 120) or not re.fullmatch(r"[\w\s.,+()\-]+", term, re.UNICODE):
        raise ValueError("search term must be general research keywords")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    key = (term.casefold(), limit)
    with _lock:
        hit = _cache.get(key)
        if hit and not force and time.monotonic() - hit[0] < TTL_SECONDS:
            return {**hit[1], "cache_hit": True}
    payload = _fetch({"query.term": term, "pageSize": limit, "format": "json",
                      "countTotal": "true"})
    fetched_at = datetime.now(timezone.utc).isoformat()
    results = []
    for study in payload.get("studies", []):
        try:
            results.append(normalize_study(study, fetched_at))
        except (ValueError, TypeError, AttributeError, KeyError):
            continue
    result = {"provider": "ClinicalTrials.gov", "query": term,
              "total_found": payload.get("totalCount"),
              "count": len(results), "records": results,
              "retrieved_at": fetched_at, "cache_hit": False,
              "interpretation": "Study registry metadata; not proof of efficacy or a diagnosis."}
    with _lock:
        _cache[key] = (time.monotonic(), result)
    return result
