"""Product snippet and merchant listing: Product, Offer, AggregateOffer, review and aggregateRating."""

from __future__ import annotations

from ...model import Item
from ...values import as_datetime, parse_price
from ..base import Context
from .base import Feature
from .merchant import check_return_policy, check_shipping
from .review import REVIEW_SNIPPET


class Product(Feature):
    id = "product"
    name = "Product snippet"
    doc = "product-snippet"
    types = ("Product",)
    required = ("name",)

    def extra(self, ctx: Context, item: Item) -> None:
        if not (item.has("offers") or item.has("review") or item.has("aggregateRating")):
            self.report(
                ctx,
                "product/offer-review-or-rating",
                "A Product needs at least one of offers, review or aggregateRating.",
                item,
            )
        offers = ctx.items_of(item, "offers")
        for offer in offers:
            self.check_offer(ctx, offer)
        for value in item.get("offers"):
            if isinstance(value, str):
                self.report(
                    ctx, "google/required", "offers must be an Offer or AggregateOffer, not text.", item, "offers"
                )
        REVIEW_SNIPPET.check_nested(ctx, item)

        # Merchant listing needs more than a product snippet. Reported as warnings: a page may only want snippets.
        if offers:
            for prop in ("image",):
                if not item.has(prop):
                    self.merchant(ctx, item, prop, f'Merchant listings need "{prop}" on the Product.')
            for offer in offers:
                if ctx.is_a(offer, "AggregateOffer"):
                    continue
                if not (ctx.present(offer, "priceCurrency") or ctx.present(offer, "priceSpecification.priceCurrency")):
                    self.merchant(ctx, offer, "priceCurrency", "Merchant listings need priceCurrency on every Offer.")
                check_shipping(ctx, offer)
                check_return_policy(ctx, offer)

    def merchant(self, ctx: Context, item: Item, prop: str | None, message: str) -> None:
        ctx.report(
            "merchant/required", message, item=item, prop=prop, feature="Merchant listing", doc_page="merchant-listing"
        )

    def check_offer(self, ctx: Context, offer: Item) -> None:
        if ctx.is_a(offer, "AggregateOffer"):
            for prop in ("lowPrice", "priceCurrency"):
                if not offer.has(prop):
                    self.report(
                        ctx,
                        "product/aggregate-offer",
                        f'Missing required property "{prop}" for an AggregateOffer.',
                        offer,
                    )
            self.check_paths(ctx, offer, ("highPrice", "offerCount"), "google/recommended", "an AggregateOffer")
            for prop in ("lowPrice", "highPrice"):
                self.check_price(ctx, offer, prop)
            return
        if not (offer.has("price") or ctx.present(offer, "priceSpecification.price")):
            self.report(
                ctx,
                "google/required",
                'Missing required property "price" (or priceSpecification.price) for an Offer.',
                offer,
            )
        self.check_paths(
            ctx,
            offer,
            ("priceCurrency|priceSpecification.priceCurrency", "availability", "priceValidUntil"),
            "google/recommended",
            "an Offer",
        )
        self.check_price(ctx, offer, "price")
        for spec in ctx.items_of(offer, "priceSpecification"):
            self.check_price(ctx, spec, "price")
        for raw in offer.texts("priceValidUntil"):
            when = as_datetime(raw)
            if when is not None and when < ctx.now:
                self.report(
                    ctx,
                    "product/price-valid-until",
                    f"priceValidUntil {raw} is in the past; the snippet may not be shown.",
                    offer,
                    "priceValidUntil",
                )

    def check_price(self, ctx: Context, item: Item, prop: str) -> None:
        for raw in item.get(prop):
            if isinstance(raw, Item):
                continue
            amount, problem = parse_price(raw)
            if problem:
                self.report(ctx, "value/price", f'{prop} "{raw}" {problem}.', item, prop)
            elif amount is not None and amount < 0:
                self.report(ctx, "value/price", f"{prop} is negative.", item, prop)
            elif amount is not None and amount == 0:
                self.report(
                    ctx,
                    "product/price-zero",
                    f"{prop} is {raw}: 0 means the product is free. Merchant listings need a price greater than 0.",
                    item,
                    prop,
                )


PRODUCT = Product()
