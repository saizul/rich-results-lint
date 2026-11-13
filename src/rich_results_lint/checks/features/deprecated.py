"""Features Google no longer shows: FAQ and How-to."""

from __future__ import annotations

from ...model import Item
from ..base import Context
from .base import Feature


class FAQPage(Feature):
    id = "faq"
    name = "FAQ"
    doc = "faqpage"
    types = ("FAQPage",)

    def check(self, ctx: Context, item: Item) -> None:
        self.report(
            ctx,
            "google/deprecated-feature",
            "FAQ rich results are no longer shown in Google Search: Google limited them to well-known government "
            "and health sites on 2023-09-14, stopped showing them on 2026-05-07 and removed the documentation on "
            "2026-06-15. The markup is still valid schema.org and other consumers may read it.",
            item,
        )
        # Basic structure, following schema.org (Google no longer publishes FAQ requirements).
        questions = ctx.items_of(item, "mainEntity")
        if not questions:
            self.report(ctx, "faq/structure", "FAQPage has no mainEntity Question items.", item, "mainEntity")
        for q in questions:
            if q.types and not ctx.is_a(q, "Question"):
                self.report(ctx, "faq/structure", f"mainEntity holds a {q.label()}; use Question.", q)
                continue
            if not q.has("name"):
                self.report(ctx, "faq/structure", "The Question has no name (the question text).", q)
            answers = ctx.items_of(q, "acceptedAnswer")
            if not answers:
                self.report(ctx, "faq/structure", "The Question has no acceptedAnswer.", q)
            for a in answers:
                if not a.has("text"):
                    self.report(ctx, "faq/structure", "The acceptedAnswer has no text.", a)


class HowTo(Feature):
    id = "howto"
    name = "How-to"
    doc = "how-to"
    types = ("HowTo",)
    exclude = ("Recipe",)

    def check(self, ctx: Context, item: Item) -> None:
        self.report(
            ctx,
            "google/deprecated-feature",
            "How-to rich results are no longer shown in Google Search; Google removed the feature and its "
            "documentation on 2023-09-14. HowTo stays valid schema.org (and HowToStep is still used in Recipe).",
            item,
        )


FAQ = FAQPage()
HOWTO = HowTo()
