"""Document text extraction — LM Studio-aligned formats (L1/L2)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

SUPPORTED_L1 = {".txt", ".docx", ".pdf"}
SUPPORTED_L2 = {".md", ".csv", ".json", ".log", ".text"}
SUPPORTED_EXTENSIONS = SUPPORTED_L1 | SUPPORTED_L2
REJECTED_EXTENSIONS = {".exe", ".zip", ".rar", ".7z", ".dll", ".bat", ".ps1", ".sh"}


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_rejected(path: Path) -> bool:
    return path.suffix.lower() in REJECTED_EXTENSIONS


def normalize_persian(text: str) -> str:
    text = text.replace("\u200c", "\u200c")  # preserve ZWNJ
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    return text


def clean_text(raw: str, *, strict: bool = False) -> str:
    raw = raw.replace("\u0000", "")
    if strict:
        return re.sub(r"[^\x20-\x7E\u0600-\u06FF\s\n\r\t]", "", raw).strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw).strip()


def extract_text(path: Path, *, strict_clean: bool = False) -> Tuple[str, str, Optional[str]]:
    """Return (text, format, error_reason)."""
    suffix = path.suffix.lower()
    fmt = suffix.lstrip(".") or "unknown"

    if is_rejected(path):
        return "", fmt, "فرمت پشتیبانی نمی‌شود"

    if suffix == ".txt" or suffix in SUPPORTED_L2:
        try:
            text = clean_text(path.read_text(encoding="utf-8", errors="ignore"), strict=strict_clean)
            text = normalize_persian(text)
            return text, fmt, None
        except OSError as exc:
            return "", fmt, str(exc)

    if suffix == ".docx":
        try:
            from docx import Document

            doc = Document(str(path))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            text = normalize_persian(clean_text("\n".join(parts), strict=strict_clean))
            return text, fmt, None
        except Exception as exc:  # pylint: disable=broad-except
            return "", fmt, f"خطا در خواندن Word: {exc}"

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            text = normalize_persian(clean_text("\n".join(parts), strict=strict_clean))
            if not text.strip():
                return "", fmt, "PDF بدون متن قابل استخراج (احتمالاً اسکن)"
            return text, fmt, None
        except Exception as exc:  # pylint: disable=broad-except
            return "", fmt, f"خطا در خواندن PDF: {exc}"

    return "", fmt, "فرمت پشتیبانی نمی‌شود"


def iter_document_paths(root: Path):
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name == ".pmo_index.json":
            continue
        if is_rejected(path):
            continue
        if is_supported(path):
            yield path


def read_documents(directory: Path, *, strict_clean: bool = False) -> str:
    parts = []
    for path in iter_document_paths(directory):
        text, _, err = extract_text(path, strict_clean=strict_clean)
        if err or not text:
            continue
        parts.append(text)
    return "\n---\n".join(parts)
