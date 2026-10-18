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

## Клинические исследования и история изменений

- `GET /research/studies?q=diabetes&limit=5` — поиск и нормализация публичных регистрационных записей ClinicalTrials.gov API v2.
- `GET /research/studies/NCT12345678/history` — сохранённые версии конкретной записи, если они действительно встречались при сборе.
- По каждому исследованию сохраняются NCT, название, статус, дата последнего обновления, тип и фаза исследования, изучаемые состояния, вмешательства, URL и SHA-256 исходной записи.
- Каждая новая контрольная сумма создаёт новую версию документа. Повтор идентичной записи не создаёт дубликата.
- Хранилище `med_history` — выделенный Docker volume с SQLite, **только метаданные общедоступных исследований**. Реальные клинические случаи и сведения о пациентах не записываются.
- `config/sources.json` фиксирует подключённые адаптеры. Для более широкого реестра см. `docs/SOURCES.md`.

### Проверка после запуска

```bash
curl -fsSG http://127.0.0.1:18091/research/studies --data-urlencode 'q=diabetes' --data-urlencode 'limit=3'
```

Выход в интернет нужен для запросов к публичным реестрам. Публикация портов ограничена `127.0.0.1`; это не защищает данные при неправильной прокси-конфигурации. Endpoint истории не содержит персональных данных.

## Автоматический сбор MED

`collector.py` — независимый обработчик двух открытых реестров. В `config/collection.json` задаются источники, поисковые запросы, лимиты и период (по умолчанию 6 часов). Не выполняет клиническую диагностику.

- `python collector.py once` — один цикл без фонового сервера.
- `python collector.py serve` — последовательный повтор каждые шесть часов.
- `med_collector` — второй Docker-сервис без публикации порта, с отдельным процессом.
- `MED_COLLECTION_DB` — локальный SQLite-журнал `collection_runs`: время, источник, запрос, успех/ошибка, число записей и новых версий.
- `MED_HISTORY_DB` — ранее созданный архив версий публичных исследований ClinicalTrials.gov.
- При ошибке отдельного запроса цикл обрабатывает остальные источники; ошибки отмечаются типом, не сохраняются медицинские данные.
- Запросы выполняются последовательно, PubMed ограничивается задержкой. Политика NCBI требует учитывать общие квоты API при росте нагрузки.
- Данные PubMed пока получаются и учитываются в журнале, но **полные версии записей PubMed не архивируются**.

После запуска контейнера можно проверить `docker logs genesis-med-collector --tail 30` и таблицу `collection_runs` в выделенном файле `/var/lib/med/collection.sqlite3`. По умолчанию сбор запускается сразу, затем по интервалу.

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

The container runs as a non-root user on its own Docker network, publishes only to VPS localhost, and has outbound access to public research registries. Its dedicated Docker volume stores **only public ClinicalTrials.gov metadata versions**, not patient cases. No GENESIS CORE or Android integration is configured. **Do not send real patient data.**

## Источники, документы и модель данных

- [Реестр источников и первичные документы](docs/SOURCES.md)
- [Планируемая структура данных и прослеживаемость](docs/DATA_MODEL.md)
- [План развития MED](docs/ROADMAP.md)
- [Машиночитаемый реестр](config/sources.json)

Статус **connected** означает реализованный адаптер, но не результат проверки подключения на VPS. Статус **candidate** — подключение ещё не выполнено.

## Future phases
- Specification of MED diagnosis-domain calculations with medical expert validation and real data schemas.
- Separate encrypted persistence with explicit provenance and retention, protected audit and access controls.
- A strictly authenticated versioned MED → CORE contract; then integration into GENESIS Android.
- Migration from shared VPS to independent MED host by changing environment networking, without embedding MED in CORE.
