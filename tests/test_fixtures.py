"""Every fixture declares what it expects in leading HTML comments:

``<!-- expect: rule/a rule/b -->``  these rules must be reported;
``<!-- max-severity: info -->``     nothing more severe than this may be reported.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rich_results_lint import Severity, lint_file

from .conftest import FIXTURES, options

ALL = sorted((FIXTURES / "valid").glob("*.html")) + sorted((FIXTURES / "invalid").glob("*.html"))


def _directives(path: Path) -> tuple[set[str], Severity | None]:
    text = path.read_text(encoding="utf-8")
    expect: set[str] = set()
    for m in re.finditer(r"<!--\s*expect:\s*(.*?)\s*-->", text):
        expect.update(m.group(1).split())
    m = re.search(r"<!--\s*max-severity:\s*(\w+)\s*-->", text)
    return expect, Severity(m.group(1)) if m else None


@pytest.mark.parametrize("path", ALL, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_fixture(path: Path) -> None:
    expect, max_severity = _directives(path)
    assert expect or max_severity, "fixture has no directives"
    doc = lint_file(path, options=options())
    found = {f.rule for f in doc.findings}
    assert expect <= found, f"missing {sorted(expect - found)}; found {sorted(found)}"
    if max_severity is not None:
        too_severe = [f"{f.rule}: {f.message}" for f in doc.findings if f.severity.rank > max_severity.rank]
        assert not too_severe, too_severe


def test_valid_fixtures_have_items() -> None:
    for path in sorted((FIXTURES / "valid").glob("*.html")):
        assert lint_file(path, options=options()).items, path.name


def test_invalid_fixtures_cover_many_rules() -> None:
    covered: set[str] = set()
    for path in ALL:
        covered.update(_directives(path)[0])
    assert len(covered) >= 60
