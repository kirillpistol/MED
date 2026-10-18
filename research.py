"""MED independent public-literature discovery; no patient data or diagnosis decisions.

Uses NCBI E-utilities esearch + esummary, with bounded queries and 10-minute
in-memory cache. Structured metadata is returned with provenance, not citations
to full texts and not clinical recommendations.
"""
from __future__ import annotations
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CACHE_TTL = 600
_cache: dict[tuple[str, int], tuple[float, dict]] = {}
_lock = threading.Lock()


def _json(endpoint: str, params: dict) -> dict:
    url = BASE + endpoint + "?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "MED-Research/1.0 (public metadata)", "Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError("source status " + str(response.status))
        return json.load(response)


def search_publications(term: str, limit: int = 5, *, force: bool = False) -> dict:
    term = term.strip()
    if not (3 <= len(term) <= 120) or not re.fullmatch(r"[\w\s.,+()\-]+", term, re.UNICODE):
        raise ValueError("search term must be public research keywords, 3-120 characters")
    if not (1 <= limit <= 10):
        raise ValueError("limit must be between 1 and 10")
    key = (term.lower(), limit)
    with _lock:
        cached = _cache.get(key)
        if cached and not force and time.monotonic() - cached[0] < CACHE_TTL:
            return {**cached[1], "cache_hit": True}
    search = _json("esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "json",
                                   "retmax": limit, "sort": "pub date"})
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not isinstance(ids, list) or any(not str(x).isdigit() for x in ids):
        raise RuntimeError("invalid source search result")
    records = []
    if ids:
        summary = _json("esummary.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
        results = summary.get("result", {})
        for uid in ids:
            row = results.get(str(uid), {})
            if not isinstance(row, dict) or not row.get("title"):
                continue
            records.append({
                "pmid": str(uid), "title": str(row["title"]),
                "journal": str(row.get("fulljournalname") or row.get("source") or ""),
                "published": str(row.get("pubdate", "")),
                "authors": [a.get("name", "") for a in row.get("authors", [])[:8] if isinstance(a, dict)],
                "url": "https://pubmed.ncbi.nlm.nih.gov/" + str(uid) + "/",
                "source": "NCBI PubMed",
                "data_kind": "publication_metadata",
            })
    payload = {
        "query": term, "count": len(records), "total_found": int(search.get("esearchresult", {}).get("count", 0)),
        "records": records, "provider": "NCBI E-utilities (PubMed)",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": "Search results are not a validated clinical evidence review or diagnosis.",
        "cache_hit": False,
    }
    with _lock:
        _cache[key] = (time.monotonic(), payload)
    return payload
