"""rich-results-lint: lint JSON-LD, Microdata and RDFa structured data against schema.org and Google's rich result
requirements."""

from __future__ import annotations

from ._version import __version__
from .fetch import FetchError, fetch
from .linter import Options, lint_file, lint_html, lint_jsonld
from .model import Document, Finding, Item, Severity, Syntax
from .rules import RULES, Rule

__all__ = [
    "RULES",
    "Document",
    "FetchError",
    "Finding",
    "Item",
    "Options",
    "Rule",
    "Severity",
    "Syntax",
    "__version__",
    "fetch",
    "lint_file",
    "lint_html",
    "lint_jsonld",
]
