from datetime import datetime
from pathlib import Path

from src.models.translation import Translation
from src.utils.export_manager import ExportManager


def make_translations():
    return [
        Translation(
            original_text="hello",
            translated_text="привет",
            source_language="en",
            target_language="ru",
            timestamp=datetime.now(),
            confidence=0.95,
        )
    ]


def test_export_json_csv_txt(tmp_path):
    m = ExportManager()
    tr = make_translations()

    fp_json = tmp_path / "out.json"
    assert m.export_translations(tr, str(fp_json), "json") is True
    assert fp_json.exists() and fp_json.read_text(encoding="utf-8").strip().startswith("{")

    fp_csv = tmp_path / "out.csv"
    assert m.export_translations(tr, str(fp_csv), "csv") is True
    assert fp_csv.exists() and "Original Text" in fp_csv.read_text(encoding="utf-8")

    fp_txt = tmp_path / "out.txt"
    assert m.export_translations(tr, str(fp_txt), "txt") is True
    assert fp_txt.exists() and "Screen Translator Export" in fp_txt.read_text(encoding="utf-8")


def test_export_xml_html(tmp_path):
    m = ExportManager()
    tr = make_translations()

    fp_xml = tmp_path / "out.xml"
    assert m.export_translations(tr, str(fp_xml), "xml") is True
    assert fp_xml.exists() and fp_xml.read_text(encoding="utf-8").lstrip().startswith("<?xml")

    fp_html = tmp_path / "out.html"
    assert m.export_translations(tr, str(fp_html), "html") is True
    assert fp_html.exists() and "<!DOCTYPE html>" in fp_html.read_text(encoding="utf-8")


def test_unsupported_format(tmp_path):
    m = ExportManager()
    tr = make_translations()
    assert m.export_translations(tr, str(tmp_path / "file.xxx"), "xxx") is False


