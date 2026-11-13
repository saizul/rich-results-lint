"""Microdata extraction (``itemscope``, ``itemtype``, ``itemprop``, ``itemid``, ``itemref``).

Follows the WHATWG Microdata algorithm closely enough for structured data testing: top-level items are elements with
``itemscope`` and no ``itemprop``; properties are the ``itemprop`` elements below an item, not crossing nested items;
``itemref`` adds the properties of the referenced elements.
"""

from __future__ import annotations

from collections.abc import Callable

from ..model import Item, Syntax, Value
from ..vocab import local_name
from .dom import Element

Report = Callable[..., None]

_URL_ATTR = {
    "a": "href",
    "area": "href",
    "link": "href",
    "audio": "src",
    "embed": "src",
    "iframe": "src",
    "img": "src",
    "source": "src",
    "track": "src",
    "video": "src",
    "object": "data",
}


def extract_microdata(root: Element, report: Report) -> list[Item]:
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    items: list[Item] = []
    for index, el in enumerate(e for e in root.iter() if e.has("itemscope") and not e.has("itemprop")):
        items.append(_item(el, f"$microdata[{index}]", by_id, report, set()))
    return items


def _item(el: Element, path: str, by_id: dict, report: Report, seen: set[int]) -> Item:
    raw_types = (el.get("itemtype") or "").split()
    if not raw_types:
        report("syntax/microdata-no-type", "This itemscope has no itemtype.", line=el.line, path=path)
    item = Item(
        types=[local_name(t) for t in raw_types], syntax=Syntax.MICRODATA, line=el.line, path=path, raw_types=raw_types
    )
    if el.get("itemid"):
        item.id = el.get("itemid")
    seen = seen | {id(el)}

    roots: list[Element] = [el]
    for ref in (el.get("itemref") or "").split():
        target = by_id.get(ref)
        if target is not None:
            roots.append(target)

    for start in roots:
        for prop_el in _property_elements(start, include_self=start is not el):
            for raw in (prop_el.get("itemprop") or "").split():
                name = local_name(raw)
                if prop_el.has("itemscope"):
                    if id(prop_el) in seen:
                        continue  # itemref loop
                    value: Value = _item(prop_el, f"{path}.{name}", by_id, report, seen)
                else:
                    value = property_value(prop_el)
                item.add(name, value, prop_el.line)
    return item


def _property_elements(start: Element, include_self: bool) -> list[Element]:
    """Elements with itemprop under ``start``, without descending into nested items."""
    out: list[Element] = []
    if include_self and start.has("itemprop"):
        out.append(start)
        if start.has("itemscope"):
            return out

    def walk(el: Element) -> None:
        for child in el.children:
            if not isinstance(child, Element):
                continue
            if child.has("itemprop"):
                out.append(child)
            if child.has("itemscope"):
                continue
            walk(child)

    walk(start)
    return out


def property_value(el: Element) -> str:
    """The Microdata value of a non-item property element."""
    # Google also reads a content attribute on any element (a common pattern on <span>).
    if el.has("content"):
        return el.get("content") or ""
    attr = _URL_ATTR.get(el.tag)
    if attr:
        return el.get(attr) or ""
    if el.tag in ("data", "meter"):
        return el.get("value") or el.text()
    if el.tag == "time" and el.has("datetime"):
        return el.get("datetime") or ""
    return el.text()
