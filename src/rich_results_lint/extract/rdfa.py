"""RDFa Lite extraction (``vocab``, ``typeof``, ``property``, ``resource``, ``prefix``).

Covers the RDFa Lite 1.1 subset that schema.org markup uses. Properties are read from ``content``, then ``href``,
``src`` or ``resource`` for links, ``datetime`` on ``<time>``, then the element text. Only schema.org terms are
kept: terms with another prefix are ignored.
"""

from __future__ import annotations

from collections.abc import Callable

from ..model import Item, Syntax
from ..vocab import is_schema_iri, local_name
from .dom import Element

Report = Callable[..., None]


def _vocab_and_prefixes(el: Element) -> tuple[str | None, dict[str, str]]:
    vocab: str | None = None
    prefixes: dict[str, str] = {}
    chain: list[Element] = []
    cur: Element | None = el
    while cur is not None:
        chain.append(cur)
        cur = cur.parent
    for node in reversed(chain):
        if node.has("vocab"):
            vocab = node.get("vocab")
        if node.has("prefix"):
            parts = (node.get("prefix") or "").split()
            for i in range(0, len(parts) - 1, 2):
                if parts[i].endswith(":"):
                    prefixes[parts[i][:-1]] = parts[i + 1]
    return vocab, prefixes


def _expand(term: str, vocab: str | None, prefixes: dict[str, str]) -> str | None:
    """Expand a term to a schema.org local name, or None when it belongs to another vocabulary."""
    if term.startswith(("http://", "https://")):
        return local_name(term) if is_schema_iri(term) else None
    if ":" in term:
        prefix, rest = term.split(":", 1)
        base = prefixes.get(prefix) or ("https://schema.org/" if prefix == "schema" else None)
        return rest if base and is_schema_iri(base) else None
    if vocab and is_schema_iri(vocab):
        return term
    return None


def extract_rdfa(root: Element, report: Report) -> list[Item]:
    items: list[Item] = []
    index = 0
    for el in root.iter():
        # Items attached to a parent with ``property`` are reached from the parent; all others are top level.
        if not el.has("typeof") or el.has("property"):
            continue
        items.append(_item(el, f"$rdfa[{index}]", report))
        index += 1
    return items


def _item(el: Element, path: str, report: Report) -> Item:
    vocab, prefixes = _vocab_and_prefixes(el)
    raw_types = (el.get("typeof") or "").split()
    types = [t for t in (_expand(r, vocab, prefixes) for r in raw_types) if t]
    if raw_types and not types:
        report(
            "syntax/rdfa-no-vocab",
            'typeof is used without vocab="https://schema.org/" or a schema: prefix.',
            line=el.line,
            path=path,
        )
    item = Item(types=types, syntax=Syntax.RDFA, line=el.line, path=path, raw_types=raw_types)
    if el.get("resource"):
        item.id = el.get("resource")

    def walk(node: Element) -> None:
        for child in node.children:
            if not isinstance(child, Element):
                continue
            if child.has("property"):
                v, p = _vocab_and_prefixes(child)
                for raw in (child.get("property") or "").split():
                    name = _expand(raw, v, p)
                    if not name:
                        continue
                    if child.has("typeof"):
                        item.add(name, _item(child, f"{path}.{name}", report), child.line)
                    else:
                        item.add(name, _value(child), child.line)
            if child.has("typeof"):
                continue  # its properties belong to the nested item
            walk(child)

    walk(el)
    return item


def _value(el: Element) -> str:
    if el.has("content"):
        return el.get("content") or ""
    for attr in ("href", "src", "resource"):
        if el.has(attr):
            return el.get(attr) or ""
    if el.tag == "time" and el.has("datetime"):
        return el.get("datetime") or ""
    return el.text()
