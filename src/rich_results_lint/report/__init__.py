"""Output formats: text, JSON and SARIF 2.1.0."""

from __future__ import annotations

from collections import Counter

from ..model import Document, Severity
from .json_report import render_json
from .sarif import render_sarif
from .text import render_text

FORMATS = {"text": render_text, "json": render_json, "sarif": render_sarif}


def summary(docs: list[Document]) -> dict:
    counts = Counter(f.severity.value for d in docs for f in d.findings)
    types = Counter(t for d in docs for item in d.items for t in (item.types or ["(untyped)"]))
    return {
        "documents": len(docs),
        "items": sum(len(d.items) for d in docs),
        "errors": counts.get(Severity.ERROR.value, 0),
        "warnings": counts.get(Severity.WARNING.value, 0),
        "infos": counts.get(Severity.INFO.value, 0),
        "types": dict(sorted(types.items())),
    }


__all__ = ["FORMATS", "render_json", "render_sarif", "render_text", "summary"]
