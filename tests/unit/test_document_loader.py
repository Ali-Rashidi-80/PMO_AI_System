"""Unit tests for document_loader."""

from pathlib import Path

import pytest

from document_loader import (
    clean_text,
    extract_text,
    is_rejected,
    is_supported,
    normalize_persian,
    read_documents,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def test_is_supported_txt():
    assert is_supported(Path("a.txt"))
    assert is_supported(Path("a.docx"))
    assert is_rejected(Path("a.exe"))


def test_normalize_persian():
    assert "ی" in normalize_persian("ي")


def test_extract_empty(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("short", encoding="utf-8")
    text, fmt, err = extract_text(p)
    assert fmt == "txt"
    assert text == "short"


def test_read_documents_skips_empty(tmp_path):
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    (tmp_path / "ok.txt").write_text("متن کافی برای ingest تست." * 2, encoding="utf-8")
    out = read_documents(tmp_path)
    assert "متن کافی" in out


@pytest.mark.skipif(not (FIX / "contract_full_fa.txt").is_file(), reason="run generate_fixtures")
def test_fixture_contract():
    text, _, err = extract_text(FIX / "contract_full_fa.txt")
    assert err is None
    assert "بند" in text


def test_clean_text_non_strict():
    assert clean_text("test 123 %", strict=False)


def test_clean_text_strict():
    assert clean_text("test 123 %", strict=True) == "test 123 %"
