"""Run extraction and all checks on a document."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .checks.base import Context
from .checks.content import check_content
from .checks.features import FEATURES, FEATURES_BY_ID
from .checks.schema import check_items
from .extract import extract_all, parse_html, parse_jsonld, visible_text
from .model import Document, Finding, Item, Severity
from .rules import RULES, matches

#: Properties through which a nested item is still a rich result candidate of its own.
ENTITY_PROPS = ("mainEntity", "breadcrumb", "video", "hasPart", "subjectOf")


@dataclass
class Options:
    """Lint options. Rule patterns accept exact ids, groups (``value``) and globs (``google/*``)."""

    select: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    #: Rule id (or pattern) to severity name.
    severity: dict[str, str] = field(default_factory=dict)
    #: Only run these features (ids from ``FEATURES_BY_ID``); empty means all.
    features: list[str] = field(default_factory=list)
    #: Compare marked-up text with the visible page text.
    content_checks: bool = True
    #: Report a page without structured data.
    report_empty: bool = True
    #: "Now", for expiry checks. Defaults to the current time.
    now: datetime | None = None

    def __post_init__(self) -> None:
        unknown = [f for f in self.features if f not in FEATURES_BY_ID]
        if unknown:
            raise ValueError(f"unknown feature(s): {', '.join(unknown)}; choose from {', '.join(FEATURES_BY_ID)}")
        for value in self.severity.values():
            if value not in {s.value for s in Severity}:
                raise ValueError(f"unknown severity {value!r}; use error, warning or info")


def lint_html(html: str, source: str = "<html>", url: str | None = None, options: Options | None = None) -> Document:
    """Lint the structured data of an HTML page."""
    opts = options or Options()
    doc = Document(source=source, url=url, html=html)
    ctx = _context(doc, opts)
    root = parse_html(html)
    doc.items = extract_all(root, _reporter(ctx))
    doc.visible_text = visible_text(root)
    _run(ctx, opts)
    return _finish(doc, opts)


def lint_jsonld(
    text: str, source: str = "<json-ld>", url: str | None = None, options: Options | None = None
) -> Document:
    """Lint a bare JSON-LD document (a ``.json`` or ``.jsonld`` file)."""
    opts = options or Options()
    doc = Document(source=source, url=url)
    ctx = _context(doc, opts)
    doc.items = parse_jsonld(text, 1, "$", _reporter(ctx))
    _run(ctx, opts)
    return _finish(doc, opts)


def lint_file(path: str | Path, options: Options | None = None, url: str | None = None) -> Document:
    p = Path(path)
    text = p.read_bytes().decode("utf-8", errors="replace")
    if p.suffix.lower() in (".json", ".jsonld"):
        return lint_jsonld(text, source=str(path), url=url, options=options)
    return lint_html(text, source=str(path), url=url, options=options)


def _context(doc: Document, opts: Options) -> Context:
    ctx = Context(doc=doc)
    if opts.now is not None:
        ctx.now = opts.now
    return ctx


def _reporter(ctx: Context):
    def report(rule: str, message: str, line: int = 0, path: str = "") -> None:
        ctx.report(rule, message, line=line, path=path)

    return report


def _index_ids(ctx: Context) -> None:
    for top in ctx.doc.items:
        for item, _ in top.walk():
            if item.id:
                ctx.ids.setdefault(item.id, []).append(item)
    # References to nodes that are only references are not resolvable.
    for key in [k for k, v in ctx.ids.items() if all(i.is_reference for i in v)]:
        del ctx.ids[key]


def candidates(ctx: Context) -> list[Item]:
    """Items that can be rich results: top-level items and items reached through ENTITY_PROPS or carousels."""
    out: list[Item] = []
    seen: set[int] = set()

    def visit(item: Item) -> None:
        item = ctx.resolve(item)  # type: ignore[assignment]
        if not isinstance(item, Item) or id(item) in seen or item.is_reference:
            return
        seen.add(id(item))
        out.append(item)
        for prop in ENTITY_PROPS:
            for child in ctx.items_of(item, prop):
                visit(child)
        if ctx.is_a(item, "ItemList") and not ctx.is_a(item, "BreadcrumbList"):
            for li in ctx.items_of(item, "itemListElement"):
                for child in ctx.items_of(li, "item"):
                    visit(child)

    for top in ctx.doc.items:
        visit(top)
    return out


def _run(ctx: Context, opts: Options) -> None:
    _index_ids(ctx)
    check_items(ctx, ctx.doc.items)
    features = [FEATURES_BY_ID[f] for f in opts.features] if opts.features else list(FEATURES)
    top_level = {id(i) for i in ctx.doc.items}
    for item in candidates(ctx):
        for feature in features:
            if feature.applies(ctx, item):
                feature.check(ctx, item)
        if opts.content_checks and id(item) in top_level:
            check_content(ctx, item)
    if opts.report_empty and not ctx.doc.items and not ctx.doc.findings:
        ctx.report("content/no-structured-data", "No JSON-LD, Microdata or RDFa structured data was found.")


def _finish(doc: Document, opts: Options) -> Document:
    findings: list[Finding] = []
    seen: set[tuple] = set()
    for f in doc.findings:
        if opts.select and not matches(f.rule, opts.select):
            continue
        if opts.ignore and matches(f.rule, opts.ignore):
            continue
        for pattern, sev in opts.severity.items():
            if matches(f.rule, [pattern]):
                f.severity = Severity(sev)
        key = (f.rule, f.line, f.path, f.message)
        if key in seen:
            continue
        seen.add(key)
        findings.append(f)
    findings.sort(key=lambda f: (f.line, -f.severity.rank, f.rule))
    doc.findings = findings
    return doc


def known_rule(rule_id: str) -> bool:
    return rule_id in RULES
