"""Machine-readable JSON output."""

from __future__ import annotations

import json

from .._version import __version__
from ..model import Document, Item


def _item(item: Item) -> dict:
    return {"types": item.types, "syntax": item.syntax.value, "line": item.line, "path": item.path, "id": item.id}


def render_json(docs: list[Document]) -> str:
    from . import summary

    payload = {
        "tool": "rich-results-lint",
        "version": __version__,
        "summary": summary(docs),
        "documents": [
            {
                "source": d.source,
                "url": d.url,
                "items": [_item(i) for i in d.items],
                "findings": [f.to_dict() for f in d.findings],
            }
            for d in docs
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
