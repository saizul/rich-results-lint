"""SARIF 2.1.0 output, for GitHub code scanning and other SARIF viewers."""

from __future__ import annotations

import json
from pathlib import Path

from .._version import __version__
from ..model import Document, Severity
from ..rules import RULES

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_LEVEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def _uri(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source
    p = Path(source)
    if p.is_absolute():
        try:
            return p.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return p.as_uri()
    return p.as_posix()


def render_sarif(docs: list[Document]) -> str:
    used = sorted({f.rule for d in docs for f in d.findings})
    index = {rule_id: i for i, rule_id in enumerate(used)}
    rules = [
        {
            "id": rule_id,
            "name": rule_id.replace("/", "-"),
            "shortDescription": {"text": RULES[rule_id].description},
            "helpUri": RULES[rule_id].help_uri,
            "defaultConfiguration": {"level": _LEVEL[RULES[rule_id].severity]},
        }
        for rule_id in used
    ]
    results = []
    for d in docs:
        for f in d.findings:
            location: dict = {"physicalLocation": {"artifactLocation": {"uri": _uri(d.source)}}}
            if f.line:
                location["physicalLocation"]["region"] = {"startLine": f.line}
            if f.path:
                location["logicalLocations"] = [{"fullyQualifiedName": f.path, "kind": "object"}]
            result = {
                "ruleId": f.rule,
                "ruleIndex": index[f.rule],
                "level": _LEVEL[f.severity],
                "message": {"text": f.message},
                "locations": [location],
            }
            props = {k: v for k, v in (("type", f.item_type), ("feature", f.feature)) if v}
            if props:
                result["properties"] = props
            results.append(result)
    log = {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "rich-results-lint",
                        "version": __version__,
                        "informationUri": "https://github.com/saizul/rich-results-lint",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(log, indent=2, ensure_ascii=False) + "\n"
