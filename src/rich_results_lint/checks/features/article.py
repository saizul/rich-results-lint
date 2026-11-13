"""Article, NewsArticle, BlogPosting (and other Article subtypes)."""

from __future__ import annotations

import re

from ...model import Item
from ..base import Context
from .base import Feature

_NOT_A_NAME = re.compile(
    r"^\s*(?:posted|written|published)\s+by\b|\bby\s*:|\s\|\s|^\s*(?:dr|mr|mrs|ms|prof)\.?\s", re.I
)
_MANY = re.compile(r"\s(?:and|&)\s|,|;")


class Article(Feature):
    id = "article"
    name = "Article"
    doc = "article"
    types = ("Article",)
    # Google lists no required properties for Article; these are its recommended ones.
    recommended = (
        "author",
        "author.name",
        "author.url|author.sameAs",
        "datePublished",
        "dateModified",
        "headline",
        "image",
    )

    def extra(self, ctx: Context, item: Item) -> None:
        for value in item.get("author"):
            author = ctx.resolve(value)
            if isinstance(author, str):
                self.report(
                    ctx,
                    "article/author",
                    f'author "{author}" is plain text; use a Person or Organization with name and url.',
                    item,
                    "author",
                )
                continue
            if not isinstance(author, Item) or author.is_reference:
                continue
            if not author.types or not ctx.is_a(author, "Person", "Organization"):
                self.report(
                    ctx,
                    "article/author",
                    f"author is {author.label()}; use Person for people and Organization for organizations.",
                    author,
                )
            for name in author.texts("name"):
                if _NOT_A_NAME.search(name):
                    self.report(
                        ctx,
                        "article/author",
                        f'author.name "{name}" should hold only the name: no "posted by", job titles or '
                        "honorifics (use jobTitle, honorificPrefix).",
                        author,
                        "name",
                    )
                elif _MANY.search(name) and ctx.is_a(author, "Person"):
                    self.report(
                        ctx,
                        "article/author",
                        f'author.name "{name}" looks like several people; give each author their own entry.',
                        author,
                        "name",
                    )
        for value in item.get("image"):
            image = ctx.resolve(value)
            if isinstance(image, Item) and not image.is_reference and not (image.has("url") or image.has("contentUrl")):
                self.report(ctx, "article/image", "The ImageObject has no url or contentUrl.", image)


ARTICLE = Article()
