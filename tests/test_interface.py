"""Static smoke tests of MED Interface 2.0 layout invariants.

These tests do not replace launching Streamlit.
"""
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "dashboard.py"

class InterfaceTests(unittest.TestCase):
    def test_report_at_top_not_sidebar(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('heading, report_area = st.columns([5, 2]', source)
        self.assertIn('st.button("Отчёт · все разделы"', source)
        self.assertNotIn('st.sidebar.button("Сформировать общий отчёт"', source)
    def test_sources_footer_after_pages(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertGreater(source.index('st.markdown("### Источники и происхождение данных")'),
                           source.index('elif section == "Документы":'))
    def test_sections_retained(self):
        source = SOURCE.read_text(encoding="utf-8")
        for section in ('"Медицинские направления"', '"Каталог источников"',
                        '"Новые источники"', '"Файлы источников"', '"Тестирование"'):
            self.assertIn(section, source)

if __name__ == "__main__":
    unittest.main()
