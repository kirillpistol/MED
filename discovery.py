"""Discover candidate medical research websites and emerging topics.

Only metadata from OpenAlex API is read. Found domains are review candidates,
never trusted sources or executable scrapers.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = "https://api.openalex.org/works"
QUERIES = ("regenerative medicine", "tissue engineering", "hematology biomarkers",
           "medical neurotechnology", "bioprinting")
DB_ENV = "MED_DISCOVERY_DB"

def _request(query: str, limit: int) -> dict:
    url = API + "?" + urlencode({"search": query, "per-page": limit,
                                  "sort": "publication_date:desc"})
    with urlopen(Request(url, headers={"Accept": "application/json",
                                       "User-Agent": "MED-ResearchCatalog/1.0"}), timeout=12) as response:
        return json.load(response)

def discover(db_path: str | None = None, queries: tuple[str, ...] = QUERIES,
             *, fetch=None, limit: int = 5) -> list[dict]:
    if not 1 <= limit <= 10:
        raise ValueError("limit must be 1..10")
    db_path = db_path or os.getenv(DB_ENV, "med-discovery.sqlite3")
    if len(queries) > 10 or any(not re.fullmatch(r"[a-zA-Z\s-]{3,80}", term) for term in queries):
        raise ValueError("invalid research topic")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    seen_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS discoveries (
            domain TEXT NOT NULL, topic TEXT NOT NULL,
            source_url TEXT NOT NULL, title TEXT NOT NULL,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate',
            PRIMARY KEY(domain, topic, source_url))""")
        results = []
        for query in queries:
            try:
                payload = (fetch or _request)(query, limit)
                count = 0
                for work in payload.get("results", [])[:limit]:
                    if not isinstance(work, dict):
                        continue
                    location = work.get("primary_location") or {}
                    page = location.get("landing_page_url") or ""
                    parsed = urlsplit(page)
                    domain = (parsed.hostname or "").lower()
                    if parsed.scheme != "https" or not domain or not re.fullmatch(r"[a-z0-9.-]{4,253}", domain):
                        continue
                    if domain in {"openalex.org", "api.openalex.org"}:
                        continue
                    title = str(work.get("title") or "")[:300]
                    conn.execute("""INSERT INTO discoveries
                        (domain,topic,source_url,title,first_seen_at,last_seen_at,status)
                        VALUES(?,?,?,?,?,?,'candidate')
                        ON CONFLICT(domain,topic,source_url) DO UPDATE SET
                            last_seen_at=excluded.last_seen_at""",
                        (domain, query, page[:500], title, seen_at, seen_at))
                    count += 1
                results.append({"topic": query, "status": "ok", "candidates_seen": count})
            except Exception as exc:
                results.append({"topic": query, "status": "error", "error_type": type(exc).__name__})
        conn.commit()
    return results

def discovery_inventory(db_path: str | None = None, limit: int = 100) -> list[dict]:
    if not 1 <= limit <= 500:
        raise ValueError("limit out of range")
    path = Path(db_path or os.getenv(DB_ENV, "med-discovery.sqlite3"))
    if not path.is_file():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute("""SELECT domain,topic,source_url,title,first_seen_at,
            last_seen_at,status FROM discoveries ORDER BY last_seen_at DESC LIMIT ?""", (limit,)).fetchall()
    columns = ("domain", "topic", "source_url", "title", "first_seen_at", "last_seen_at", "status")
    return [dict(zip(columns, row)) for row in rows]
