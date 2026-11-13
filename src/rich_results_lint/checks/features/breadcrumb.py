"""BreadcrumbList."""

from __future__ import annotations

from ...model import Item
from ...values import parse_number
from ..base import Context
from .base import Feature


class Breadcrumb(Feature):
    id = "breadcrumb"
    name = "Breadcrumb"
    doc = "breadcrumb"
    types = ("BreadcrumbList",)
    required = ("itemListElement",)

    def extra(self, ctx: Context, item: Item) -> None:
        elements = ctx.items_of(item, "itemListElement")
        if not item.has("itemListElement"):
            return
        if len(elements) < 2:
            self.report(
                ctx,
                "breadcrumb/items",
                f"The breadcrumb has {len(elements)} ListItem; Google needs at least two.",
                item,
                "itemListElement",
            )
        positioned: list[tuple[float, Item]] = []
        seen: set[float] = set()
        for el in elements:
            if el.types and not ctx.is_a(el, "ListItem"):
                self.report(ctx, "breadcrumb/items", f"itemListElement holds a {el.label()}; use ListItem.", el)
            raw = el.first("position")
            if raw is None:
                self.report(ctx, "google/required", 'Missing required property "position" for a ListItem.', el)
                continue
            pos = parse_number(raw)
            if pos is None or pos != int(pos):
                self.report(ctx, "breadcrumb/position", f'position "{raw}" is not an integer.', el, "position")
                continue
            if pos in seen:
                self.report(ctx, "breadcrumb/position", f"position {int(pos)} is used twice.", el, "position")
            seen.add(pos)
            positioned.append((pos, el))
        positioned.sort(key=lambda p: p[0])
        if positioned and positioned[0][0] != 1:
            self.report(
                ctx,
                "breadcrumb/position",
                f"Positions start at {int(positioned[0][0])}; the first breadcrumb must be position 1.",
                positioned[0][1],
                "position",
            )
        for i, (pos, el) in enumerate(positioned):
            if i and pos != positioned[i - 1][0] + 1:
                self.report(
                    ctx,
                    "breadcrumb/position",
                    f"Position {int(positioned[i - 1][0])} is followed by {int(pos)}; positions should be consecutive.",
                    el,
                    "position",
                )
                break
        for i, (_pos, el) in enumerate(positioned):
            last = i == len(positioned) - 1
            targets = el.get("item")
            target = ctx.resolve(targets[0]) if targets else None
            if target is None and not last:
                self.report(
                    ctx,
                    "breadcrumb/item",
                    'Missing "item" (the URL of this breadcrumb); only the last breadcrumb may leave it out.',
                    el,
                )
            if isinstance(target, Item) and not (target.id or target.has("url") or target.has("@id")) and not last:
                self.report(ctx, "breadcrumb/item", "The item has no @id or url, so it has no URL.", el, "item")
            named = el.has("name") or (isinstance(target, Item) and target.has("name"))
            if not named:
                self.report(ctx, "google/required", 'Missing required property "name" for a ListItem.', el)


BREADCRUMB = Breadcrumb()
