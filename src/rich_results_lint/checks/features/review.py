"""Review snippet: Review and AggregateRating, on their own or nested in the reviewed item."""

from __future__ import annotations

import re

from ...model import Item
from ...values import parse_number, parse_rating
from ..base import Context, text_of
from .base import Feature, info

#: Types (and their subtypes) Google supports as itemReviewed for review snippets.
REVIEWABLE = (
    "Book",
    "Course",
    "CreativeWorkSeason",
    "CreativeWorkSeries",
    "Episode",
    "Event",
    "Game",
    "HowTo",
    "LocalBusiness",
    "MediaObject",
    "Movie",
    "MusicPlaylist",
    "MusicRecording",
    "Organization",
    "Product",
    "Recipe",
    "SoftwareApplication",
)
_PROMO = re.compile(r"\d+\s*%|\b(?:off|sale|discount|deal|coupon|offer|free shipping|buy now|cheap)\b|https?://", re.I)


class ReviewSnippet(Feature):
    id = "review"
    name = "Review snippet"
    doc = "review-snippet"
    types = ("Review", "AggregateRating")

    def applies(self, ctx: Context, item: Item) -> bool:
        # Ratings nested in other items are checked from the parent with check_nested().
        return ctx.is_a(item, "Review", "AggregateRating")

    def extra(self, ctx: Context, item: Item) -> None:
        if ctx.is_a(item, "AggregateRating"):
            self.check_aggregate(ctx, item, parent=None)
        else:
            self.check_review(ctx, item, parent=None)

    def check(self, ctx: Context, item: Item) -> None:
        self.extra(ctx, item)

    def check_nested(self, ctx: Context, parent: Item) -> None:
        """Check ``review`` and ``aggregateRating`` of an item that is itself the reviewed item."""
        for review in ctx.items_of(parent, "review"):
            self.check_review(ctx, review, parent)
        for rating in ctx.items_of(parent, "aggregateRating"):
            self.check_aggregate(ctx, rating, parent)

    # Review --------------------------------------------------------------------------------------------------

    def check_review(self, ctx: Context, review: Item, parent: Item | None) -> None:
        required = ["author", "author.name", "reviewRating", "reviewRating.ratingValue"]
        if parent is None:
            required += ["itemReviewed", "itemReviewed.name"]
        self.check_paths(ctx, review, tuple(required), "google/required", "a Review")
        self.check_paths(ctx, review, ("datePublished",), "google/recommended", "a Review")
        self.check_item_reviewed(ctx, review, parent)
        for author in ctx.items_of(review, "author"):
            self.check_author(ctx, author)
        for value in review.get("author"):
            if isinstance(value, str):
                self.report(
                    ctx,
                    "review/author-name",
                    f'author "{value}" is text; use a Person or Organization with a name.',
                    review,
                    "author",
                )
                self.check_author_name(ctx, review, value)
        for rating in ctx.items_of(review, "reviewRating"):
            self.check_range(ctx, rating)

    def check_author(self, ctx: Context, author: Item) -> None:
        if author.types and not ctx.is_a(author, "Person", "Organization"):
            self.report(
                ctx,
                "review/author-name",
                f"The review author is a {author.label()}; use Person or Organization.",
                author,
            )
        for name in author.texts("name"):
            self.check_author_name(ctx, author, name)

    def check_author_name(self, ctx: Context, item: Item, name: str) -> None:
        if len(name) >= 100:
            self.report(ctx, "review/author-name", "The author name must be shorter than 100 characters.", item, "name")
        elif _PROMO.search(name):
            self.report(
                ctx,
                "review/author-name",
                f'The author name "{name}" looks like a promotion, not a person or organization.',
                item,
                "name",
            )

    def check_item_reviewed(self, ctx: Context, review: Item, parent: Item | None) -> None:
        targets = [parent] if parent is not None else ctx.items_of(review, "itemReviewed")
        for target in targets:
            if target.types and not ctx.is_a(target, *REVIEWABLE):
                self.report(
                    ctx,
                    "review/item-type",
                    f"{target.label()} is not a type Google shows review snippets for "
                    "(Product, Recipe, LocalBusiness, Book, Course, Event, Movie, SoftwareApplication ...).",
                    review,
                )
        if parent is not None and review.get("itemReviewed"):
            info(
                ctx,
                self,
                "review/item-type",
                "itemReviewed is set on a nested review; Google asks for one way of naming the reviewed item.",
                review,
                "itemReviewed",
            )

    # AggregateRating -----------------------------------------------------------------------------------------

    def check_aggregate(self, ctx: Context, rating: Item, parent: Item | None) -> None:
        required = ["ratingValue", "ratingCount|reviewCount"]
        if parent is None:
            required += ["itemReviewed", "itemReviewed.name"]
        self.check_paths(ctx, rating, tuple(required), "google/required", "an AggregateRating")
        self.check_item_reviewed(ctx, rating, parent)
        self.check_range(ctx, rating)
        for prop in ("ratingCount", "reviewCount"):
            for v in rating.get(prop):
                n = parse_number(v)
                if n is not None and n <= 0:
                    self.report(ctx, "review/rating-range", f"{prop} is {v}; it must be at least 1.", rating, prop)

    def check_range(self, ctx: Context, rating: Item) -> None:
        best = parse_number(rating.first("bestRating")) if rating.has("bestRating") else None
        worst = parse_number(rating.first("worstRating")) if rating.has("worstRating") else None
        for raw in rating.get("ratingValue"):
            if isinstance(raw, Item) or raw is None:
                continue
            value, implied_best = parse_rating(raw)
            if value is None:
                self.report(ctx, "value/number", f'ratingValue "{raw}" is not a number.', rating, "ratingValue")
                continue
            if isinstance(raw, str) and re.fullmatch(r"\d+,\d+", raw.strip()):
                info(
                    ctx,
                    self,
                    "value/number",
                    f'ratingValue "{raw}" uses a decimal comma; use "{raw.replace(",", ".")}".',
                    rating,
                    "ratingValue",
                )
            hi = best if best is not None else (implied_best or 5.0)
            lo = worst if worst is not None else (0.0 if implied_best else 1.0)
            if not lo <= value <= hi:
                scale = "" if best is not None or implied_best else " (the default scale is 1 to 5; set bestRating)"
                self.report(
                    ctx,
                    "review/rating-range",
                    f"ratingValue {text_of(raw)} is outside {lo:g} to {hi:g}{scale}.",
                    rating,
                    "ratingValue",
                )
        if best is not None and worst is not None and worst >= best:
            self.report(ctx, "review/rating-range", "worstRating must be lower than bestRating.", rating, "worstRating")


REVIEW_SNIPPET = ReviewSnippet()


def check_self_serving(ctx: Context, feature: Feature, item: Item) -> None:
    """LocalBusiness and Organization ratings about themselves are not eligible for stars."""
    for prop in ("review", "aggregateRating"):
        if item.has(prop):
            feature.report(
                ctx,
                "review/self-serving",
                f"{item.label()} has {prop}. Review snippets are not shown for reviews a business or organization "
                "publishes about itself, including embedded third-party widgets.",
                item,
                prop,
            )
