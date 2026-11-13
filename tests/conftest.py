from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from rich_results_lint import Document, Options, lint_html, lint_jsonld

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def options(**kw) -> Options:
    kw.setdefault("now", NOW)
    return Options(**kw)


def lint(html: str, **kw) -> Document:
    url = kw.pop("url", None)
    return lint_html(html, source="test.html", url=url, options=options(**kw))


def lint_ld(data: str, **kw) -> Document:
    return lint_jsonld(data, source="test.jsonld", options=options(**kw))


def page(jsonld: str, body: str = "") -> str:
    return f'<html><head><script type="application/ld+json">{jsonld}</script></head><body>{body}</body></html>'


def rules(doc: Document) -> set[str]:
    return {f.rule for f in doc.findings}


def messages(doc: Document, rule: str) -> list[str]:
    return [f.message for f in doc.findings if f.rule == rule]


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
