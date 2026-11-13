"""Content mismatch hints: marked-up values that do not appear on the page.

Google requires structured data to describe content that is visible to users. These checks compare a few key
values of JSON-LD items with the visible text of the page. They are hints (severity ``info``): text can be rendered
by JavaScript, abbreviated or formatted differently, so a miss is not always a problem.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from ..model import Item, Syntax
from ..values import parse_price
from .base import Context

#: Properties whose text should be visible, by type.
VISIBLE_PROPS = {
    "Product": ("name",),
    "Article": ("headline",),
    "Recipe": ("name",),
    "Event": ("name",),
    "JobPosting": ("title",),
    "LocalBusiness": ("name",),
    "VideoObject": ("name",),
    "Question": ("name",),
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[‘’“”'\"`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def check_content(ctx: Context, item: Item) -> None:
    if item.syntax is not Syntax.JSON_LD or not ctx.doc.visible_text:
        return
    page = normalize(ctx.doc.visible_text)
    for type_name, props in VISIBLE_PROPS.items():
        if not ctx.is_a(item, type_name):
            continue
        for prop in props:
            for text in item.texts(prop):
                needle = normalize(text)
                if len(needle) < 4:
                    continue
                # Long values are often trimmed on the page: compare the first 60 characters.
                if needle[:60] not in page:
                    ctx.report(
                        "content/not-visible",
                        f'{prop} "{text[:80]}" does not appear in the visible page text. Structured data must describe '
                        "content users can see.",
                        item=item,
                        prop=prop,
                    )
    if ctx.is_a(item, "Product"):
        for offer in ctx.items_of(item, "offers"):
            for prop in ("price", "lowPrice"):
                for raw in offer.get(prop):
                    amount, problem = parse_price(raw)
                    if amount is None or problem or amount == 0:
                        continue
                    if not _price_visible(amount, ctx.doc.visible_text):
                        ctx.report(
                            "content/price-mismatch",
                            f"{prop} {raw} does not appear in the visible page text.",
                            item=offer,
                            prop=prop,
                        )


def _price_visible(amount: Decimal, text: str) -> bool:
    digits_in_page = {re.sub(r"[,\s ]", "", m) for m in re.findall(r"\d[\d,\s ]*(?:\.\d+)?", text)}
    candidates = {format(amount.normalize(), "f")}
    if amount == amount.to_integral():
        candidates.add(str(int(amount)))
        candidates.add(f"{int(amount)}.00")
    else:
        candidates.add(f"{amount:.2f}")
    for found in digits_in_page:
        found = found.rstrip(".")
        try:
            if Decimal(found) == amount:
                return True
        except ArithmeticError:
            continue
    return any(c in digits_in_page for c in candidates)
