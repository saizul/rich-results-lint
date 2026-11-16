"""Software app: SoftwareApplication, MobileApplication, WebApplication and VideoGame."""

from __future__ import annotations

from ...model import Item
from ...values import parse_price
from ...vocab import local_name
from ..base import Context
from .base import Feature
from .review import REVIEW_SNIPPET

#: applicationCategory values listed in Google's software app documentation.
CATEGORIES = frozenset(
    {
        "GameApplication",
        "SocialNetworkingApplication",
        "TravelApplication",
        "ShoppingApplication",
        "SportsApplication",
        "LifestyleApplication",
        "BusinessApplication",
        "DesignApplication",
        "DeveloperApplication",
        "DriverApplication",
        "EducationalApplication",
        "HealthApplication",
        "FinanceApplication",
        "SecurityApplication",
        "BrowserApplication",
        "CommunicationApplication",
        "DesktopEnhancementApplication",
        "EntertainmentApplication",
        "MultimediaApplication",
        "HomeApplication",
        "UtilitiesApplication",
        "ReferenceApplication",
    }
)
_BY_LOWER = {c.lower(): c for c in CATEGORIES}


class SoftwareApp(Feature):
    id = "software-app"
    name = "Software app"
    doc = "software-app"
    # A VideoGame only qualifies when it is co-typed with SoftwareApplication (checked in extra()).
    types = ("SoftwareApplication", "VideoGame")
    required = ("name", "offers", "offers.price|offers.lowPrice")
    recommended = ("applicationCategory", "operatingSystem")

    def extra(self, ctx: Context, item: Item) -> None:
        names = {local_name(t) for t in item.types}
        if "VideoGame" in names and not names & {"SoftwareApplication", "MobileApplication", "WebApplication"}:
            self.report(
                ctx,
                "software/video-game",
                'A VideoGame must also be typed as SoftwareApplication: "@type": ["VideoGame", "SoftwareApplication"].',
                item,
            )
        if not (item.has("aggregateRating") or item.has("review")):
            self.report(
                ctx,
                "software/rating",
                "A software app needs aggregateRating or review to be eligible for the rich result.",
                item,
            )
        for value in item.get("offers"):
            if isinstance(ctx.resolve(value), str):
                self.report(ctx, "google/required", "offers is text; use an Offer with a price.", item, "offers")
        for offer in ctx.items_of(item, "offers"):
            for raw in offer.get("price"):
                if isinstance(raw, Item):
                    continue
                amount, problem = parse_price(raw)
                if problem is None and amount is not None and amount > 0 and not offer.has("priceCurrency"):
                    self.report(
                        ctx,
                        "google/required",
                        "offers.priceCurrency is required when the price is greater than 0.",
                        offer,
                        "price",
                    )
        for raw in item.texts("applicationCategory"):
            self.check_category(ctx, item, raw)
        REVIEW_SNIPPET.check_nested(ctx, item)

    def check_category(self, ctx: Context, item: Item, raw: str) -> None:
        name = local_name(raw.strip())
        if name in CATEGORIES:
            return
        guess = _BY_LOWER.get(name.lower()) or _BY_LOWER.get(name.lower().replace(" ", "") + "application")
        hint = f' Did you mean "{guess}"?' if guess else ""
        self.report(
            ctx,
            "software/category",
            f'applicationCategory "{raw}" is not one of the categories Google supports (GameApplication, '
            f"BusinessApplication, UtilitiesApplication ...).{hint}",
            item,
            "applicationCategory",
        )


SOFTWARE_APP = SoftwareApp()
