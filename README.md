# MED — самостоятельный расчётный модуль

**MED is independent of GENESIS CORE, L2 and L3.** It can run on a shared test VPS today or migrate to an independent host later. No production integration, real traffic capture, patient information, VPN provisioning, or medical diagnosis occurs in this release.

## Pipeline
1. Accept an **explicitly synthetic** JSON case with bounded enumerated observations.
2. Validate it (no free-text names, IDs restricted to simple local case IDs; duplicate feature codes rejected).
3. Apply deterministic weighted overlaps against three **illustrative syndrome patterns**, not medical diagnostic classes.
4. Return ranked pattern matches, trace metadata, algorithm version and SHA-256 input fingerprint.
5. Return optional JSON report. No persistent storage at this stage.

Scores are similarity measures **not calibrated probabilities**. No clinical use, diagnosis, treatment or triage is authorized. Real clinical deployment would require clinician-led scope definition, dataset provenance, validation and applicable privacy/security compliance.

## Automated public literature discovery

Read-only PubMed metadata search using NCBI E-utilities (esearch + esummary). The query, authors, journal, publication date, PMID, direct URL, retrieval timestamp and search hit count are returned in a structured response. The results are cached for ten minutes in memory, at most ten per request. No patient records are submitted to this service.

The source registry is `config/sources.json`. PubMed is implemented; ClinicalTrials.gov is listed as a **candidate**, not connected. Public literature metadata is not a clinically validated diagnostic calculation and is not automatically used for ranking syndrome patterns.

Try when MED is running:

```bash
curl -fsSG 'http://127.0.0.1:18091/research/publications' --data-urlencode 'q=machine learning diagnosis' --data-urlencode 'limit=5'
```

## Local tests
From repository root with Python and FastAPI installed:

```bash
python -m unittest discover -s tests -v
```

## Independent VPS Docker test
On the existing Linux test VPS after pulling updated branch, without touching GENESIS API:

```bash
cd /opt/med-release
docker compose -f compose.yml up -d --build
curl -fsS http://127.0.0.1:18091/healthz
curl -fsS -X POST http://127.0.0.1:18091/analyze -H 'Content-Type: application/json' -d '{"case_id":"demo-001","synthetic":true,"observations":[{"code":"fever","present":true},{"code":"cough","present":true}]}'
```

If host port publishing is unavailable (as occurred with a previous internal-network-only test), verify inside the container:
```bash
docker exec genesis-med-standalone python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8091/healthz').read().decode())"
```

The container has its own internal network, no access to the existing GENESIS API network, runs as a non-root user, does not mount secrets, and has no persistent data volume. **Do not send real patient data.**

## Future phases
- Specification of MED diagnosis-domain calculations with medical expert validation and real data schemas.
- Separate encrypted persistence with explicit provenance and retention, protected audit and access controls.
- A strictly authenticated versioned MED → CORE contract; then integration into GENESIS Android.
- Migration from shared VPS to independent MED host by changing environment networking, without embedding MED in CORE.
