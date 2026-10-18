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

## MED Analytics — статистика архивированных исследований

`GET /analytics/studies` возвращает количественный отчёт по **локально сохранённой выборке** ClinicalTrials.gov: число уникальных NCT, количество версий документов, распределение последних известных статусов набора участников и фаз исследований, список случаев изменения записей. Для каждой изменённой записи возвращаются обе контрольные суммы и признаки изменения статуса.

Расчёт детерминирован по существующим версиям SQLite и не требует запроса внешнего API. Отчёт описывает **только собранную локальную выборку**, поэтому не может использоваться для оценки заболеваемости, распространённости или эффективности лечения.

`analytics.py` — отдельный расчётный модуль, `tests/test_analytics.py` — тестирование версий, изменений и пустой базы.

## MED Dashboard — самостоятельный интерфейс (как MESM)

Интерактивная панель Streamlit `dashboard.py`: **Обзор**, **Исследования**, **Аналитика**, **Документы** и **Тестирование**. Интерфейс русскоязычный; загружает публичные метаданные из PubMed и ClinicalTrials.gov, просматривает результаты SQLite Analytics, выполняет ручной цикл сборщика, показывает версионность NCT и экспортирует JSON-отчёт.

### Запуск на Windows PowerShell

```powershell
git clone https://github.com/kirillpistol/MED.git
cd MED
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:MED_HISTORY_DB = "$PWD\med-history.sqlite3"
$env:MED_COLLECTION_DB = "$PWD\med-collection.sqlite3"
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Откройте `http://localhost:8501`. Если установлен Python под именем `python`, замените `py` в команде создания окружения на `python`. Вносить реальную медицинскую информацию пациентов нельзя.

### На независимом Docker стенде

После клонирования MED на Linux, из корня репозитория:

```bash
docker compose up -d --build
docker compose ps
docker logs genesis-med-dashboard --tail 60
```

Dashboard доступен **только на серверном localhost:18501**, без публичного проброса. Чтобы открыть в браузере Windows с известного тестового VPS, сделайте SSH-туннель в отдельном PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" -L 18501:127.0.0.1:18501 root@194.67.120.173
```

Откройте `http://localhost:18501`. Не публикуйте интерфейс наружу без отдельной аутентификации и настройки доступа. Настоящая эксплуатация на VPS и успешная проверка тестов пока не подтверждены.

### Что проверить вручную

1. **Обзор** — нулевые показатели до сборки, обновление запускает цикл публичных источников.
2. **Исследования** — выбор PubMed/ClinicalTrials.gov, поиск терминов, ссылка на оригинал и дата получения.
3. **Аналитика** — количество исследований, версии, статусы, фазы и изменения.
4. **Документы** — скачивание агрегированного JSON и история NCT.
5. **Тестирование** — локальные команды проверки; страница не подменяет реальный прогон unit-тестов.

## Отчёт MED Research

`GET /reports/research` создаёт JSON-отчёт по локальному архиву общедоступных записей ClinicalTrials.gov. Он содержит описание алгоритмов подсчёта, количества записей и версий, изменения статусов, первичный источник, ограничения анализа и воспроизводимую контрольную сумму SHA-256 содержимого отчёта без временной метки. В Dashboard → «Документы» тот же отчёт доступен для скачивания.

Проверка: `python -m unittest discover -s tests -v`, в том числе `tests/test_reports.py`. Это исследовательская статистика, а не модель медицинской диагностики. Прогон после последних изменений ещё не подтверждён.

## MED Quality — контроль качества источников

`GET /quality/studies` проверяет **метаданные сохранённых публичных исследований**: формат NCT, ссылку на оригинал, наличие названия и статуса, дату последнего обновления, формат контрольной суммы и согласованность полей с архивом. Результат содержит число проверенных записей, прошедших и записей с замечаниями, а также категории ошибок. Модуль `quality.py` работает без сетевого подключения по локальному архиву; проверки `tests/test_quality.py` используют только синтетические данные.

Результат встроен в **MED Dashboard → Аналитика**, а также в JSON-отчёт раздела «Документы». Контроль качества метаданных не является проверкой достоверности клинических выводов, диагнозов или результатов исследований. Успешное прохождение тестов на Windows/VPS ещё не подтверждено.

## Сводный отчёт по всем разделам MED

В боковом меню Dashboard находится кнопка **«Сформировать общий отчёт»**, после которой доступна загрузка `med-full-report.json`. В разделе **«Документы»** тот же агрегированный отчёт формируется сразу. Отчёт объединяет: общую статистику локального архива, контроль качества исходных записей, динамику статусов исследований, тематический анализ и описание методов и источников.

## Медицинские направления

Раздел Dashboard **«Медицинские направления»** поддерживает пять отдельных областей:
- Кровь и гематология.
- Заболевания.
- Повреждения.
- Восстановление тканей (регенеративная медицина).
- Технологии улучшения функций организма (протезирование, интерфейсы, ассистивные технологии).

Для каждой области есть тематический поиск в PubMed / ClinicalTrials.gov и расчёт числа совпадений в **локально архивированных** публичных исследованиях. Тематические совпадения основаны на ключевых словах, поэтому могут пересекаться и **не оценивают эффективность, безопасность процедур или индивидуальные медицинские показатели**.

Модуль `themes.py` и тесты `tests/test_themes.py` доступны в репозитории. Добавленные расчёты не работают с данными анализов крови пациентов; для этого понадобится отдельная согласованная предметная модель, клинические референсные интервалы и валидированные источники.

## Расширенный каталог медицинских источников

Новые источники РФ, регенеративной медицины, биопринтинга и нейроинтерфейсов добавлены как **кандидаты** в `config/extended_sources.json` и отображаются в Dashboard → «Каталог источников». Пока это только проверяемый перечень: подключения, скачивания данных и установки сторонних проектов нет. Описание и порядок подключения: [docs/EXTENDED_SOURCES.md](docs/EXTENDED_SOURCES.md). Тесты: `tests/test_source_catalog.py`.

## Приём файлов и обновление источников

- Существующий `collector.py` выполняет автоматические запросы к PubMed и ClinicalTrials.gov по расписанию (конфигурация `config/collection.json`). Этот сбор начинает работать после запуска `med_collector`.
- `config/file_sources.json` — отдельный реестр **прямых адресов файлов**, пока пустой. Для загрузок необходимо проверить официальные URL и условия доступа; ссылки на главные страницы не являются URL файлов.
- `file_registry.py` регистрирует **уже полученные локальные CSV/JSON/XML** размером не более 5 МБ и сохраняет SHA-256 и историю версий в SQLite. Он не отправляет запросы в сеть и не копирует содержимое файлов в базу.
- `tests/test_file_registry.py` проверяет дедупликацию и запрет неподдерживаемых расширений.
- Dashboard → **«Файлы источников»** показывает учтённые версии из `MED_FILES_DB`, по умолчанию `med-files.sqlite3`.
- Автоматическое скачивание файлов **ещё не реализовано**. Сначала нужен один проверенный официальный прямой URL выгрузки и документ с условиями использования.

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
