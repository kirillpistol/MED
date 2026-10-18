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
from clinical_trials import search_studies
from history import archive_public_studies, study_history
from research import search_publications
from collector import run_cycle, _config

st.set_page_config(page_title="MED · Research Dashboard", page_icon="🩺", layout="wide")

st.markdown("""
<style>
:root { color-scheme: light; }
.block-container { max-width: 1180px; padding-top: 2rem; }
div[data-testid="stMetric"] {
  background: #f0f1f2; border: 1px solid #d9dcdf;
  border-radius: 14px; padding: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("MED")
st.caption("Независимый медицинский исследовательский модуль · L3")
st.info("Исследовательский стенд. Данные реестров и демонстрационные расчёты не являются диагнозом или рекомендацией по лечению.")

section = st.sidebar.radio("Разделы", ["Обзор", "Исследования", "Аналитика", "Медицинские направления", "Каталог источников", "Документы", "Тестирование"])
st.sidebar.caption("MED работает независимо от CORE, L2 и приложения GENESIS.")
st.sidebar.markdown("### Сводка MED")
if st.sidebar.button("Сформировать общий отчёт", type="primary", use_container_width=True):
    st.session_state["med_consolidated_report"] = generate_research_report()
if "med_consolidated_report" in st.session_state:
    st.sidebar.download_button("Скачать общую сводку · JSON",
        json.dumps(st.session_state["med_consolidated_report"], ensure_ascii=False, indent=2),
        file_name="med-full-report.json", mime="application/json", use_container_width=True)
    st.sidebar.caption("Отчёт сформирован по локальному архиву; сетевые запросы отдельно.")


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

elif section == "Документы":
    st.subheader("Единая сводка MED · все разделы")
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
