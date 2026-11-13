"""JSON-LD extraction: ``<script type="application/ld+json">`` blocks or bare JSON-LD files."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from ..model import Item, Syntax, Value
from ..vocab import is_schema_iri, local_name
from .dom import Element
from .jsonpos import PosDict, loads_with_lines

Report = Callable[..., None]

KEYWORDS = {
    "@context",
    "@id",
    "@type",
    "@graph",
    "@value",
    "@language",
    "@list",
    "@set",
    "@reverse",
    "@index",
    "@base",
    "@vocab",
    "@nest",
    "@included",
    "@direction",
    "@json",
    "@none",
}
_WRAPPER = re.compile(r"^\s*(?:<!--|//\s*<!\[CDATA\[|/\*\s*<!\[CDATA\[\s*\*/)|(?:-->|//\s*\]\]>|/\*\s*\]\]>\s*\*/)\s*$")


def is_jsonld_script(el: Element) -> bool:
    if el.tag != "script":
        return False
    t = (el.get("type") or "").split(";")[0].strip().lower()
    return t == "application/ld+json"


def extract_from_dom(root: Element, report: Report) -> list[Item]:
    items: list[Item] = []
    for index, el in enumerate(e for e in root.iter() if is_jsonld_script(e)):
        text = "".join(c for c in el.children if isinstance(c, str))
        items.extend(parse_jsonld(text, el.line, f"$script[{index}]", report))
    return items


def parse_jsonld(text: str, first_line: int, path: str, report: Report) -> list[Item]:
    """Parse one JSON-LD document into items. Problems are sent to ``report``."""
    cleaned = _WRAPPER.sub("", text.strip()) if text.strip() else ""
    if not cleaned.strip():
        report("syntax/empty-script", "The JSON-LD script is empty.", line=first_line, path=path)
        return []
    # Keep line numbers: count the lines removed in front of the JSON.
    offset = text[: text.find(cleaned.strip()[:1])].count("\n") if cleaned.strip() else 0
    try:
        data = loads_with_lines(cleaned.strip(), first_line + offset)
    except json.JSONDecodeError as exc:
        report(
            "syntax/json-invalid",
            f"Invalid JSON: {exc.msg} (line {exc.lineno} column {exc.colno} of the script).",
            line=first_line + offset + exc.lineno - 1,
            path=path,
        )
        return []
    except (ValueError, RecursionError) as exc:  # pragma: no cover - json.loads accepted it
        report("syntax/json-invalid", f"Could not parse the JSON-LD: {exc}.", line=first_line, path=path)
        return []

    converter = _Converter(report)
    tops = data if isinstance(data, list) else [data]
    items: list[Item] = []
    for i, node in enumerate(tops):
        node_path = f"{path}[{i}]" if isinstance(data, list) else path
        if not isinstance(node, dict):
            report(
                "syntax/json-ld-shape",
                f"Expected a JSON object, found {type(node).__name__}.",
                line=first_line,
                path=node_path,
            )
            continue
        context = node.get("@context")
        if context is None:
            report(
                "syntax/missing-context",
                'No "@context": add "@context": "https://schema.org".',
                line=_line(node, first_line),
                path=node_path,
            )
        elif not _is_schema_context(context):
            report(
                "syntax/unknown-context",
                f"@context {json.dumps(context)[:80]} does not point to schema.org.",
                line=_line(node, first_line),
                path=node_path,
            )
        if "@graph" in node:
            graph = node["@graph"]
            for j, g in enumerate(graph if isinstance(graph, list) else [graph]):
                if isinstance(g, dict):
                    item = converter.item(g, f"{node_path}.@graph[{j}]", first_line)
                    if item is not None:
                        items.append(item)
            others = {k: v for k, v in node.items() if k not in ("@context", "@graph")}
            if others and ("@type" in others or len(others) > 1):
                item = converter.item(PosDict(others), node_path, _line(node, first_line))
                if item is not None:
                    items.append(item)
            continue
        item = converter.item(node, node_path, first_line)
        if item is not None:
            items.append(item)
    return items


def _line(node: dict, default: int) -> int:
    return getattr(node, "line", default)


def _is_schema_context(context: object) -> bool:
    if isinstance(context, str):
        return is_schema_iri(context.rstrip("/") + "/")
    if isinstance(context, list):
        return any(_is_schema_context(c) for c in context)
    if isinstance(context, dict):
        vocab = context.get("@vocab")
        if isinstance(vocab, str) and is_schema_iri(vocab):
            return True
        return any(isinstance(v, str) and is_schema_iri(v) for v in context.values())
    return False


class _Converter:
    def __init__(self, report: Report) -> None:
        self.report = report

    def item(self, node: dict, path: str, fallback_line: int) -> Item | None:
        line = _line(node, fallback_line)
        raw_type = node.get("@type")
        raw_types = [t for t in (raw_type if isinstance(raw_type, list) else [raw_type]) if isinstance(t, str)]
        item = Item(
            types=[local_name(t) for t in raw_types],
            syntax=Syntax.JSON_LD,
            line=line,
            path=path,
            raw_types=raw_types,
        )
        node_id = node.get("@id")
        if isinstance(node_id, str):
            item.id = node_id
        key_lines = getattr(node, "key_lines", {})
        for key, value in node.items():
            if key.startswith("@"):
                if key not in KEYWORDS:
                    self.report(
                        "syntax/unknown-keyword",
                        f'"{key}" is not a JSON-LD keyword. Did you mean "{key[1:]}"?',
                        line=key_lines.get(key, line),
                        path=f"{path}.{key}",
                    )
                continue
            name = local_name(key)
            if name != key or ":" not in key:
                item.raw_names[name] = key
            for v in self.values(value, f"{path}.{name}", key_lines.get(key, line)):
                item.add(name, v, key_lines.get(key, line))
        item.is_reference = bool(item.id) and not item.types and not item.properties
        return item

    def values(self, value: object, path: str, line: int) -> list[Value]:
        if isinstance(value, list):
            out: list[Value] = []
            for i, v in enumerate(value):
                out.extend(self.values(v, f"{path}[{i}]", line))
            return out
        if isinstance(value, dict):
            if "@value" in value:
                inner = value["@value"]
                return [inner if isinstance(inner, (str, int, float, bool)) or inner is None else str(inner)]
            if "@list" in value or "@set" in value:
                return self.values(value.get("@list", value.get("@set")), path, line)
            nested = self.item(value, path, line)
            return [nested] if nested is not None else []
        if isinstance(value, (str, int, float, bool)) or value is None:
            return [value]
        return [str(value)]
