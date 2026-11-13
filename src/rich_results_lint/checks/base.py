"""Shared helpers for the checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..model import Document, Finding, Item, Severity, Value
from ..rules import GOOGLE_DOCS, RULES
from ..vocab import Vocabulary, get_vocabulary


@dataclass
class Context:
    """Everything a check needs: the document, the vocabulary, the clock and the findings list."""

    doc: Document
    vocab: Vocabulary = field(default_factory=get_vocabulary)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    #: Items by @id, for resolving node references.
    ids: dict[str, list[Item]] = field(default_factory=dict)

    def report(
        self,
        rule: str,
        message: str,
        item: Item | None = None,
        prop: str | None = None,
        line: int | None = None,
        path: str | None = None,
        feature: str = "",
        severity: Severity | None = None,
        doc_page: str | None = None,
    ) -> None:
        r = RULES[rule]
        if line is None:
            line = item.line_of(prop) if item is not None and prop else (item.line if item is not None else 0)
        if path is None:
            path = item.path if item is not None else ""
            if prop:
                path = f"{path}.{prop}"
        help_uri = GOOGLE_DOCS + doc_page if doc_page else r.help_uri
        self.doc.findings.append(
            Finding(
                rule=rule,
                severity=severity or r.severity,
                message=message,
                source=self.doc.source,
                line=line,
                path=path,
                item_type=item.label() if item is not None else "",
                feature=feature,
                help_uri=help_uri,
            )
        )

    def resolve(self, value: Value) -> Value:
        """Follow a node reference to the node it names, when it is defined on the page."""
        if isinstance(value, Item) and value.is_reference and value.id in self.ids:
            for candidate in self.ids[value.id]:
                if not candidate.is_reference:
                    return candidate
        return value

    def items_of(self, item: Item, prop: str) -> list[Item]:
        return [v for v in (self.resolve(x) for x in item.get(prop)) if isinstance(v, Item)]

    def values(self, item: Item, path: str) -> list[Value]:
        """Values at a dotted path (``offers.price``), following nested items and node references."""
        current: list[Value] = [item]
        for part in path.split("."):
            nxt: list[Value] = []
            for v in current:
                v = self.resolve(v)
                if isinstance(v, Item):
                    nxt.extend(self.resolve(x) for x in v.get(part))
            current = nxt
        return current

    def present(self, item: Item, path: str) -> bool:
        from ..model import is_empty

        return any(not is_empty(v) for v in self.values(item, path))

    def is_a(self, item: Item, *types: str) -> bool:
        return any(self.vocab.is_subtype(t, *types) for t in item.types)


def text_of(value: Value) -> str | None:
    if value is None or isinstance(value, (Item, bool)):
        return None
    return str(value)
