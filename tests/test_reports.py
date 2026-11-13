from __future__ import annotations

import json

from rich_results_lint.report import render_json, render_sarif, render_text, summary
from rich_results_lint.rules import RULES

from .conftest import FIXTURES, lint, options


def docs():
    from rich_results_lint import lint_file

    return [
        lint_file(FIXTURES / "invalid" / "values.html", options=options()),
        lint_file(FIXTURES / "valid" / "product.html", options=options()),
    ]


def test_text_report() -> None:
    out = render_text(docs())
    assert "values.html:" in out
    assert "error value/date:" in out
    assert out.strip().splitlines()[-1].startswith(tuple("0123456789"))
    assert "in 2 documents" in out
    assert "\033[" not in out


def test_text_report_color_and_verbose() -> None:
    out = render_text(docs(), color=True, verbose=True)
    assert "\033[31m" in out
    assert "product.html  (1 item: Product)" in out


def test_json_report() -> None:
    data = json.loads(render_json(docs()))
    assert data["tool"] == "rich-results-lint"
    assert data["summary"]["documents"] == 2
    assert data["summary"]["errors"] > 0
    first = data["documents"][0]
    assert first["items"][0]["syntax"] == "json-ld"
    f = first["findings"][0]
    assert set(f) == {"rule", "severity", "message", "source", "line", "path", "type", "feature", "help"}


def test_sarif_report_structure() -> None:
    data = json.loads(render_sarif(docs()))
    assert data["version"] == "2.1.0"
    run = data["runs"][0]
    driver = run["tool"]["driver"]
    assert driver["name"] == "rich-results-lint"
    ids = [r["id"] for r in driver["rules"]]
    assert ids == sorted(set(ids))
    for result in run["results"]:
        assert result["ruleId"] in RULES
        assert driver["rules"][result["ruleIndex"]]["id"] == result["ruleId"]
        assert result["level"] in ("error", "warning", "note")
        loc = result["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"].endswith(".html")
        assert loc["region"]["startLine"] >= 1


def test_sarif_with_url_source_and_no_findings() -> None:
    doc = lint("<html></html>", ignore=["content"])
    doc.source = "https://example.com/"
    data = json.loads(render_sarif([doc]))
    assert data["runs"][0]["results"] == []
    assert data["runs"][0]["tool"]["driver"]["rules"] == []


def test_summary_counts_types() -> None:
    s = summary(docs())
    assert s["types"]["Product"] == 1
    assert s["items"] == 2


def test_every_rule_has_description_and_valid_id() -> None:
    import re

    for rule_id, rule in RULES.items():
        assert re.fullmatch(r"[a-z]+/[a-z0-9-]+", rule_id), rule_id
        assert rule.description.endswith((".", "...")), rule_id
