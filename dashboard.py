"""MED Dashboard — independent L3 workstation for public research metadata.

Run: streamlit run dashboard.py
No patient records and no clinical diagnosis decisions.
"""
import json
import os
import sqlite3
from pathlib import Path
import streamlit as st

from analytics import study_analytics
from reports import generate_research_report
from quality import archive_quality
from themes import THEMES, summarize_themes
from source_catalog import source_catalog
from file_registry import file_inventory
from discovery import discover, discovery_inventory
from clinical_trials import search_studies
from history import archive_public_studies, study_history
from research import search_publications
from collector import run_cycle, _config
from collector_status import collection_status
from documents import publish_report, list_reports

st.set_page_config(page_title="MED · Research Dashboard", page_icon="🩺", layout="wide")

st.markdown("""
<style>
/* MED Interface 2.0: MESM-aligned compact, clear monochrome layout */
.block-container { max-width: 1320px; padding-top: 1.45rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(125,125,125,.22); }
[data-testid="stMetric"] {
  border: 1px solid rgba(125,125,125,.22);
  background: rgba(125,125,125,.055);
  border-radius: 9px; padding: 15px;
}
[data-testid="stMetricLabel"] { font-weight: 500; }
[data-testid="stDataFrame"] { border: 1px solid rgba(125,125,125,.2); border-radius: 8px; }
.stButton button, [data-testid="stDownloadButton"] button { border-radius: 7px; }
h1, h2, h3 { letter-spacing: -.025em; }
</style>
""", unsafe_allow_html=True)

sections = ["Обзор", "Исследования", "Аналитика", "Медицинские направления",
            "Каталог источников", "Новые источники", "Файлы источников",
            "Документы", "Тестирование"]
section = st.sidebar.radio("MED · Разделы", sections)
st.sidebar.caption("L3 · самостоятельный исследовательский модуль")
st.sidebar.caption("CORE / L2 подключаются отдельно")

heading, report_area = st.columns([5, 2], vertical_alignment="center")
with heading:
    st.title("MED")
    st.caption("MEDICAL RESEARCH SYSTEM  /  L3  /  RESEARCH DASHBOARD")
with report_area:
    if st.button("Отчёт · все разделы", type="primary", use_container_width=True):
        st.session_state["med_consolidated_report"] = generate_research_report()
    if "med_consolidated_report" in st.session_state:
        if st.button("Сохранить в каталог документов", use_container_width=True):
            st.session_state["med_published_document"] = publish_report(st.session_state["med_consolidated_report"])
        st.download_button("Скачать сводный отчёт", json.dumps(
            st.session_state["med_consolidated_report"], ensure_ascii=False, indent=2),
            "med-full-report.json", mime="application/json", use_container_width=True)
st.caption("Раздел: " + section + "  /  Источники, методы и история обновлений — внизу каждой страницы")
st.divider()
st.info("Исследовательские метаданные и демонстрационные модели. Не предназначено для постановки диагноза или назначения лечения.")


def summary():
    return study_analytics()

if section == "Обзор":
    st.subheader("Состояние MED")
    data = summary()
    cols = st.columns(4)
    for col, label, value in zip(cols,
          ["Исследований", "Версий документов", "Изменявшихся записей", "Статус архива"],
          [data["studies"], data["archived_versions"], data["changed_studies"],
           "Доступен" if data["archive_available"] else "Нет данных"]):
        col.metric(label, value)
    st.markdown("### Контур сбора")
    st.write("**PubMed** — публикации и библиографические сведения.")
    st.write("**ClinicalTrials.gov** — исследования, статусы, фазы и версии записей.")
    try:
        config = _config()
        st.caption(f"Интервал сбора: {config['schedule_hours']} ч · запросов: {len(config['queries'])}")
    except (OSError, ValueError, KeyError) as err:
        st.warning("Конфигурация сборщика недоступна: " + type(err).__name__)
    if st.button("Обновить данные сейчас", type="primary"):
        with st.spinner("Выполняется сбор по открытым реестрам..."):
            result = run_cycle()
        st.dataframe(result, use_container_width=True, hide_index=True)
        if any(row["status"] != "ok" for row in result):
            st.warning("Часть запросов завершилась ошибкой. Проверьте тип ошибки в журнале.")
        else:
            st.success("Цикл завершён.")
    st.caption("Показатели основаны только на локально сохранённых публичных записях.")

elif section == "Исследования":
    st.subheader("Поиск открытых исследований")
    source = st.radio("Источник", ["ClinicalTrials.gov", "PubMed"], horizontal=True)
    term = st.text_input("Ключевые слова", value="clinical decision support", max_chars=120)
    limit = st.slider("Число результатов", 1, 10, 5)
    if st.button("Найти исследования", type="primary"):
        try:
            with st.spinner("Обращаемся к открытому реестру..."):
                if source == "ClinicalTrials.gov":
                    data = search_studies(term, limit)
                    archived = archive_public_studies(data["records"])
                    st.caption("Новых сохранённых версий: " + str(archived["inserted_versions"]))
                else:
                    data = search_publications(term, limit)
            st.write("Найдено по запросу:", data.get("total_found", "—"))
            st.caption("Источник: " + data["provider"] + " · получено: " + data["retrieved_at"])
            for item in data["records"]:
                title = item.get("title") or "Без названия"
                with st.expander(title):
                    st.json(item)
                    st.markdown(f"[Открыть первичный источник]({item['url']})")
            if not data["records"]:
                st.info("По этому запросу нет записей.")
        except ValueError as exc:
            st.error("Некорректный запрос: " + str(exc))
        except Exception:
            st.error("Источник временно недоступен. Повторите запрос позже.")

elif section == "Аналитика":
    st.subheader("Аналитика открытых клинических исследований")
    data = summary()
    a, b, c = st.columns(3)
    a.metric("Уникальные NCT", data["studies"])
    b.metric("Архивных версий", data["archived_versions"])
    c.metric("Изменённых исследований", data["changed_studies"])
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Статусы исследований")
        if data["status_counts"]:
            st.bar_chart(data["status_counts"])
        else:
            st.info("Запустите сбор, чтобы получить показатели.")
    with col_b:
        st.markdown("#### Фазы исследований")
        if data["phase_counts"]:
            st.bar_chart(data["phase_counts"])
        else:
            st.info("Нет данных по фазам.")
    st.markdown("#### Качество архивных метаданных")
    quality = archive_quality()
    st.write("Проверено:", quality["checked"], "· Пройдено:", quality["passed"], "· С замечаниями:", quality["failed"])
    if quality["issue_counts"]:
        st.dataframe([{"Проблема": key, "Количество": count} for key, count in quality["issue_counts"].items()], hide_index=True)
    st.markdown("#### Изменения документов")
    if data["changes"]:
        st.dataframe(data["changes"], use_container_width=True, hide_index=True)
    else:
        st.caption("Пока не зарегистрировано нескольких версий одной записи.")
    st.caption("Это статистика собранной выборки, не показатель заболеваемости или эффективности.")

elif section == "Медицинские направления":
    st.subheader("Направления медицинских исследований")
    selected = st.selectbox("Раздел", list(THEMES.keys()),
                            format_func=lambda key: THEMES[key]["name"])
    theme = THEMES[selected]
    st.caption("Поиск публикаций и исследований; не индивидуальная медицинская диагностика.")
    local = summarize_themes()["themes"][selected]
    c1, c2 = st.columns(2)
    c1.metric("Исследований в локальной выборке", local["matched_studies"])
    c2.metric("Всего тематических направлений", len(THEMES))
    if local["status_counts"]:
        st.bar_chart(local["status_counts"])
    if local["examples"]:
        st.dataframe(local["examples"], use_container_width=True, hide_index=True)
    st.markdown("#### Новые исследования")
    source = st.radio("Источник", ["PubMed", "ClinicalTrials.gov"], horizontal=True,
                      key="theme_source")
    query = st.text_input("Поисковый запрос", value=theme["query"], max_chars=120,
                          key="theme_query_" + selected)
    if st.button("Найти публикации по направлению", type="primary"):
        try:
            with st.spinner("Получение общедоступных метаданных..."):
                response = search_publications(query, 5) if source == "PubMed" else search_studies(query, 5)
            st.caption("Источник: " + response["provider"] + " · " + response["retrieved_at"])
            for record in response["records"]:
                with st.expander(record.get("title") or "Без названия"):
                    st.json(record)
                    st.markdown("[Первичный источник](" + record["url"] + ")")
            if not response["records"]:
                st.info("По запросу нет результатов.")
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Источник временно недоступен.")
    st.caption("Тематическая классификация выполняется по ключевым словам. Совпадения могут пересекаться.")

elif section == "Каталог источников":
    st.subheader("Реестр источников MED")
    st.caption("Новые ресурсы пока являются кандидатами: подключение и загрузка не выполняются.")
    category_labels = {"russia": "Государственные ресурсы РФ",
                       "regenerative": "Регенеративная медицина и протеомика",
                       "bioprinting": "Биопринтинг",
                       "neuro": "Нейроинтерфейсы"}
    category = st.selectbox("Группа", list(category_labels), format_func=lambda item: category_labels[item])
    catalog = source_catalog(category=category)
    st.metric("Источников в разделе", catalog["count"])
    for entry in catalog["sources"]:
        with st.expander(entry["name"]):
            st.write("Категория данных:", entry["data_kind"])
            st.write("Статус:", entry["status"], "· Проверка:", entry["validation"])
            st.write("Условия доступа:", entry["access"])
            st.markdown("[Открыть ресурс](" + entry["url"] + ")")
            if entry.get("companion"):
                st.markdown("[Документация / сторонний проект](" + entry["companion"] + ")")
    st.info("Каталог не загружает содержимое, не запускает сторонние парсеры и не хранит персональные данные.")

elif section == "Новые источники":
    st.subheader("Обнаружение новых исследовательских ресурсов")
    st.caption("Поиск через OpenAlex. Находки — кандидаты; доверенными источниками автоматически не становятся.")
    if st.button("Найти новые сайты и направления", type="primary"):
        with st.spinner("Поиск публичных исследовательских метаданных..."):
            st.dataframe(discover(), hide_index=True, use_container_width=True)
    entries = discovery_inventory()
    st.metric("Кандидатов в локальной очереди", len(entries))
    if entries:
        st.dataframe(entries, use_container_width=True, hide_index=True)
    else:
        st.info("Запустите поиск или фоновый сборщик, чтобы сформировать перечень.")

elif section == "Файлы источников":
    st.subheader("Версии файлов источников")
    st.caption("Учёт локально полученных официальных файлов. Автоматическая загрузка по URL пока не активирована.")
    file_db = Path(os.environ.get("MED_FILES_DB", "med-files.sqlite3"))
    versions = file_inventory(file_db)
    st.metric("Учтённых версий", len(versions))
    if versions:
        st.dataframe(versions, use_container_width=True, hide_index=True)
    else:
        st.info("Файлы пока не зарегистрированы. Сначала необходимо подтвердить прямые ссылки выгрузок и условия их использования.")
    st.code("python -c \"from pathlib import Path; from file_registry import register_file; print(register_file(Path('sample.csv'), 'official_source', Path('med-files.sqlite3')))\"", language="bash")

elif section == "Документы":
    st.subheader("Единая сводка MED · все разделы")
    st.markdown("#### Каталог опубликованных отчётов")
    stored = list_reports()["documents"]
    if stored:
        st.dataframe(stored, use_container_width=True, hide_index=True)
    else:
        st.info("Каталог пока пуст. Сформируйте и сохраните отчёт через кнопку сверху.")
    data = generate_research_report()
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button("Скачать полный отчёт JSON", payload, "med-full-report.json",
                       mime="application/json")
    st.caption("Обзор, аналитика, качество записей и все пять исследовательских направлений, источники, методы, ограничения.")
    for theme in data["research_themes"]["themes"].values():
        st.write("**" + theme["name"] + "** — исследований в локальной выборке: " + str(theme["matched_studies"]))
    st.markdown("#### История исследования")
    nct = st.text_input("Идентификатор NCT", placeholder="NCT12345678")
    if nct:
        import re
        if not re.fullmatch(r"NCT[0-9]{8}", nct):
            st.warning("Формат идентификатора: NCT и 8 цифр.")
        else:
            versions = study_history(nct)
            st.write("Сохранено версий:", len(versions))
            for idx, version in enumerate(versions):
                with st.expander("Версия " + str(idx + 1) + " · " + version["first_seen_at"]):
                    st.json(version)
    st.markdown("#### Документация MED")
    st.write("Реестр источников: `config/sources.json`")
    st.write("Методика: `docs/DATA_MODEL.md`; справочники: `docs/SOURCES.md`.")
    st.write("Развитие: `docs/ROADMAP.md`.")
    st.caption("Отчёт содержит агрегированные метаданные публичного реестра, без медицинских данных пациентов.")

else:
    st.subheader("Проверки MED")
    st.write("Доступность локального архива:", "Да" if summary()["archive_available"] else "Нет")
    st.code("python -m unittest discover -s tests -v", language="bash")
    st.write("Проверка API: `GET /healthz`, `GET /analytics/studies`.")
    st.write("Проверка сборщика: `python collector.py once`.")
    st.warning("Прогон unit-тестов выполняется в терминале. Появление страницы не означает, что тесты прошли.")

# Сквозной нижний блок источников — на каждой странице MED, как в MESM.
st.divider()
st.markdown("### Источники и происхождение данных")
source_rows = [
    {"Источник": "PubMed / NCBI", "Назначение": "Библиографические сведения", "Подключение": "API реализован"},
    {"Источник": "ClinicalTrials.gov", "Назначение": "Исследования и версии NCT", "Подключение": "API реализован"},
    {"Источник": "OpenAlex", "Назначение": "Обнаружение сайтов и тематик", "Подключение": "Кандидаты на проверке"},
    {"Источник": "Расширенный каталог MED", "Назначение": "Справочники РФ, биотехнологии и нейроархивы", "Подключение": "17 кандидатов"},
]
st.dataframe(source_rows, use_container_width=True, hide_index=True)
status = collection_status()
st.caption("Журнал автообновлений: " + status["description"])
if status["latest"]:
    st.dataframe(status["latest"], use_container_width=True, hide_index=True)
st.caption("Результаты автоматически найденных страниц не считаются медицинскими рекомендациями. Новые источники требуют проверки.")
