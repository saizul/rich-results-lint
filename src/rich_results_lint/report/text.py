"""Human-readable output, one line per finding."""

from __future__ import annotations

from ..model import Document, Severity

_LABEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "info"}
_COLOR = {Severity.ERROR: "\033[31m", Severity.WARNING: "\033[33m", Severity.INFO: "\033[36m"}
_RESET = "\033[0m"


def render_text(docs: list[Document], color: bool = False, verbose: bool = False) -> str:
    from . import summary

    lines: list[str] = []
    for doc in docs:
        if verbose or doc.findings:
            types = ", ".join(sorted({t for i in doc.items for t in i.types})) or "no items"
            lines.append(f"{doc.source}  ({len(doc.items)} item{'s' if len(doc.items) != 1 else ''}: {types})")
        for f in doc.findings:
            label = _LABEL[f.severity]
            if color:
                label = f"{_COLOR[f.severity]}{label}{_RESET}"
            where = f"{doc.source}:{f.line}" if f.line else doc.source
            context = f" [{f.item_type}]" if f.item_type else ""
            lines.append(f"  {where}: {label} {f.rule}: {f.message}{context}")
    s = summary(docs)
    plural = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"  # noqa: E731
    lines.append(
        f"{plural(s['errors'], 'error')}, {plural(s['warnings'], 'warning')}, {plural(s['infos'], 'info')} "
        f"in {plural(s['documents'], 'document')} ({plural(s['items'], 'item')})"
    )
    return "\n".join(lines) + "\n"
