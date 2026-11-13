"""Structured data extraction from HTML: JSON-LD, Microdata and RDFa."""

from __future__ import annotations

from collections.abc import Callable

from ..model import Item
from .dom import Element, parse_html, visible_text
from .jsonld import extract_from_dom, parse_jsonld
from .microdata import extract_microdata
from .rdfa import extract_rdfa

__all__ = ["Element", "extract_all", "parse_html", "parse_jsonld", "visible_text"]


def extract_all(root: Element, report: Callable[..., None]) -> list[Item]:
    """All top-level items of a page, JSON-LD first, then Microdata, then RDFa."""
    return extract_from_dom(root, report) + extract_microdata(root, report) + extract_rdfa(root, report)
