"""A small, forgiving HTML tree built with the standard library parser.

Only what the extractors need: tags, attributes, text, source lines and parent links. Unclosed elements are closed
when an ancestor closes, the way browsers recover from most broken markup.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
RAW_TEXT = {"script", "style"}
#: Deeper elements are attached to the element at this depth, which keeps every tree walk well within recursion limits.
MAX_DEPTH = 256
#: Elements whose text is not shown to users.
HIDDEN = {"script", "style", "noscript", "template", "head", "title", "meta", "link"}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    line: int
    parent: Element | None = None
    children: list[Element | str] = field(default_factory=list)

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def has(self, name: str) -> bool:
        return name in self.attrs

    def iter(self) -> Iterator[Element]:
        """This element and all descendant elements in document order."""
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.iter()

    def text(self) -> str:
        parts: list[str] = []
        self._collect(parts)
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def _collect(self, parts: list[str]) -> None:
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                child._collect(parts)


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {}, 1)
        self.stack: list[Element] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        values = {k.lower(): (v if v is not None else "") for k, v in attrs}
        el = Element(tag.lower(), values, line, parent=self.stack[-1])
        self.stack[-1].children.append(el)
        if el.tag not in VOID and len(self.stack) < MAX_DEPTH:
            self.stack.append(el)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        values = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.stack[-1].children.append(Element(tag.lower(), values, line, parent=self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return
        # Stray end tag: ignore it.

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse_html(html: str) -> Element:
    """Parse HTML into an :class:`Element` tree rooted at a ``#document`` element."""
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def visible_text(root: Element) -> str:
    """Text a visitor can see: everything except scripts, styles, templates, the head and ``hidden`` elements."""
    parts: list[str] = []

    def walk(el: Element) -> None:
        if el.tag in HIDDEN or el.has("hidden") or el.get("aria-hidden") == "true":
            return
        style = (el.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            return
        for child in el.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                walk(child)
                if child.tag in {"p", "div", "li", "br", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}:
                    parts.append(" ")

    walk(root)
    return re.sub(r"\s+", " ", "".join(parts)).strip()
