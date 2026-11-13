"""Base class for Google rich result feature checks."""

from __future__ import annotations

from ...model import Item, Severity
from ..base import Context


class Feature:
    """One Google Search rich result feature.

    ``required`` and ``recommended`` hold dotted property paths. ``a|b`` means "a or b". A nested path such as
    ``offers.price`` is only checked when its parent (``offers``) is present; list the parent on its own to require it.
    """

    id: str = ""
    name: str = ""
    #: Page under https://developers.google.com/search/docs/appearance/structured-data/
    doc: str = ""
    types: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    recommended: tuple[str, ...] = ()

    def applies(self, ctx: Context, item: Item) -> bool:
        return ctx.is_a(item, *self.types) and not (self.exclude and ctx.is_a(item, *self.exclude))

    def check(self, ctx: Context, item: Item) -> None:
        self.check_paths(ctx, item, self.required, "google/required")
        self.check_paths(ctx, item, self.recommended, "google/recommended")
        self.extra(ctx, item)

    def extra(self, ctx: Context, item: Item) -> None:
        """Feature-specific checks."""

    # Helpers ---------------------------------------------------------------------------------------------------

    def report(self, ctx: Context, rule: str, message: str, item: Item, prop: str | None = None, **kw) -> None:
        ctx.report(rule, message, item=item, prop=prop, feature=self.name, doc_page=self.doc, **kw)

    def check_paths(
        self, ctx: Context, item: Item, paths: tuple[str, ...], rule: str, label: str | None = None
    ) -> None:
        kind = "required" if rule == "google/required" else "recommended"
        for spec in paths:
            alternatives = spec.split("|")
            if any(ctx.present(item, alt) for alt in alternatives):
                continue
            # Nested paths are skipped when the parent is missing: the parent is reported on its own.
            parents = {alt.rsplit(".", 1)[0] for alt in alternatives if "." in alt}
            if parents and not any(ctx.present(item, p) for p in parents):
                continue
            shown = " or ".join(f'"{a}"' for a in alternatives)
            self.report(
                ctx,
                rule,
                f"Missing {kind} property {shown} for {label or self.name}.",
                item,
                prop=alternatives[0].split(".")[0] if "." in alternatives[0] else None,
            )

    def nested_paths(self, ctx: Context, item: Item, prop: str, paths: tuple[str, ...], rule: str, label: str) -> None:
        """Check paths on each nested item under ``prop``."""
        for child in ctx.items_of(item, prop):
            self.check_paths(ctx, child, paths, rule, label)


def warn(ctx: Context, feature: Feature, rule: str, message: str, item: Item, prop: str | None = None) -> None:
    feature.report(ctx, rule, message, item, prop, severity=Severity.WARNING)


def info(ctx: Context, feature: Feature, rule: str, message: str, item: Item, prop: str | None = None) -> None:
    feature.report(ctx, rule, message, item, prop, severity=Severity.INFO)
