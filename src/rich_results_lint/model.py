"""Data model shared by the extractors, the checks and the reporters."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Union

Literal = Union[str, int, float, bool, None]  # noqa: UP007 - runtime alias
Value = Union["Item", Literal]


class Severity(str, Enum):
    """Finding severity. ``error`` makes an item ineligible for its rich result."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 3, "warning": 2, "info": 1}[self.value]


class Syntax(str, Enum):
    JSON_LD = "json-ld"
    MICRODATA = "microdata"
    RDFA = "rdfa"


@dataclass
class Item:
    """A structured data node: one JSON-LD object, Microdata ``itemscope`` or RDFa ``typeof``.

    ``types`` and property names are schema.org local names (``Product``, ``offers``); prefixes and the
    ``https://schema.org/`` namespace are removed by the extractors. ``raw_types`` keeps the strings as written.
    """

    types: list[str]
    syntax: Syntax
    line: int = 0
    path: str = "$"
    id: str | None = None
    properties: dict[str, list[Value]] = field(default_factory=dict)
    raw_types: list[str] = field(default_factory=list)
    #: Property names as written (prefixed or full IRIs), keyed by local name.
    raw_names: dict[str, str] = field(default_factory=dict)
    #: True for JSON-LD node references such as ``{"@id": "#org"}`` with no other properties.
    is_reference: bool = False
    #: Line of each property, when the syntax gives one (Microdata, RDFa).
    property_lines: dict[str, int] = field(default_factory=dict)
    #: Properties whose value came from an attribute or text that the extractor could not read.
    notes: list[str] = field(default_factory=list)

    def add(self, name: str, value: Value, line: int | None = None) -> None:
        self.properties.setdefault(name, []).append(value)
        if line is not None:
            self.property_lines.setdefault(name, line)

    def get(self, name: str) -> list[Value]:
        return self.properties.get(name, [])

    def first(self, name: str) -> Value:
        values = self.properties.get(name)
        return values[0] if values else None

    def has(self, name: str) -> bool:
        """True when the property is present with at least one non-empty value."""
        return any(not is_empty(v) for v in self.properties.get(name, []))

    def items(self, name: str) -> list[Item]:
        return [v for v in self.properties.get(name, []) if isinstance(v, Item)]

    def texts(self, name: str) -> list[str]:
        out: list[str] = []
        for v in self.properties.get(name, []):
            if isinstance(v, Item):
                continue
            if v is not None and not isinstance(v, bool):
                out.append(str(v))
        return out

    def is_a(self, *names: str) -> bool:
        return any(t in names for t in self.types)

    def line_of(self, name: str) -> int:
        return self.property_lines.get(name, self.line)

    def label(self) -> str:
        if self.types:
            return "/".join(self.types)
        return "@id reference" if self.is_reference else "(untyped)"

    def walk(self) -> Iterator[tuple[Item, str]]:
        """This item and every nested item, with their property paths."""
        yield self, self.path
        for values in self.properties.values():
            for v in values:
                if isinstance(v, Item):
                    yield from v.walk()


def is_empty(value: Value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Item):
        return not value.properties and not value.id and not value.types
    return False


@dataclass
class Finding:
    """One problem found in the structured data."""

    rule: str
    severity: Severity
    message: str
    source: str = ""
    line: int = 0
    path: str = ""
    item_type: str = ""
    feature: str = ""
    help_uri: str = ""

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "line": self.line,
            "path": self.path,
            "type": self.item_type,
            "feature": self.feature,
            "help": self.help_uri,
        }


@dataclass
class Document:
    """An HTML page (or a bare JSON-LD file) and what was extracted from it."""

    source: str
    url: str | None = None
    html: str = ""
    items: list[Item] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    #: Visible text of the page, for content mismatch hints.
    visible_text: str = ""
