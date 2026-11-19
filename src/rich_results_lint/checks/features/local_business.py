"""LocalBusiness and its subtypes (Restaurant, Store, ...), and Organization."""

from __future__ import annotations

import re

from ...model import Item
from ...values import decimals, parse_number
from ..base import Context
from .base import Feature
from .merchant import check_return_policy
from .review import check_self_serving

DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "PublicHolidays"}
_TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$|^24:00(?::00)?$")
_PHONE_OK = re.compile(r"^\+\d[\d\s().-]{5,}$")


class LocalBusiness(Feature):
    id = "local-business"
    name = "Local business"
    doc = "local-business"
    types = ("LocalBusiness",)
    required = ("address", "name")
    recommended = (
        "address.streetAddress",
        "address.addressLocality",
        "address.postalCode",
        "address.addressCountry",
        "geo",
        "geo.latitude",
        "geo.longitude",
        "openingHoursSpecification",
        "telephone",
        "url",
        "priceRange",
    )

    def extra(self, ctx: Context, item: Item) -> None:
        if ctx.is_a(item, "FoodEstablishment"):
            self.check_paths(ctx, item, ("servesCuisine", "menu|hasMenu"), "google/recommended")
        for value in item.get("address"):
            if isinstance(value, str):
                self.report(
                    ctx,
                    "google/required",
                    "address is plain text; use a PostalAddress with streetAddress, addressLocality, postalCode and "
                    "addressCountry.",
                    item,
                    "address",
                )
        for geo in ctx.items_of(item, "geo"):
            for prop in ("latitude", "longitude"):
                for v in geo.get(prop):
                    places = decimals(v)
                    if places is not None and places < 5:
                        self.report(
                            ctx, "local/geo", f"{prop} {v} has {places} decimal places; use at least 5.", geo, prop
                        )
                    n = parse_number(v)
                    limit = 90 if prop == "latitude" else 180
                    if n is not None and abs(n) > limit:
                        self.report(ctx, "local/geo", f"{prop} {v} is out of range.", geo, prop)
        for spec in ctx.items_of(item, "openingHoursSpecification"):
            self.check_hours(ctx, spec)
        for phone in item.texts("telephone"):
            if not _PHONE_OK.match(phone.strip()):
                self.report(
                    ctx,
                    "local/telephone",
                    f'telephone "{phone}" should start with + and the country code, e.g. "+8802..." or "+1212...".',
                    item,
                    "telephone",
                )
        for price_range in item.texts("priceRange"):
            if len(price_range) >= 100:
                self.report(
                    ctx,
                    "local/price-range",
                    "priceRange is 100 characters or longer; Google will not show it.",
                    item,
                    "priceRange",
                )
        check_self_serving(ctx, self, item)

    def check_hours(self, ctx: Context, spec: Item) -> None:
        for day in spec.texts("dayOfWeek"):
            name = day.rsplit("/", 1)[-1]
            if name not in DAYS:
                self.report(
                    ctx,
                    "local/opening-hours",
                    f'dayOfWeek "{day}" is not a schema.org day (use "Monday" ... "Sunday" or https://schema.org/Monday).',
                    spec,
                    "dayOfWeek",
                )
        for prop in ("opens", "closes"):
            for t in spec.texts(prop):
                if not _TIME.match(t.strip()):
                    self.report(
                        ctx,
                        "local/opening-hours",
                        f'{prop} "{t}" is not a 24-hour time such as "09:00" or "21:30:00".',
                        spec,
                        prop,
                    )
        if not spec.has("dayOfWeek"):
            self.report(ctx, "local/opening-hours", "openingHoursSpecification has no dayOfWeek.", spec)


class Organization(Feature):
    id = "organization"
    name = "Organization"
    doc = "organization"
    types = ("Organization",)
    exclude = ("LocalBusiness",)
    # Google lists no required properties. These are the recommended ones that most affect the knowledge panel.
    recommended = ("name", "url", "logo", "sameAs", "address", "contactPoint|telephone|email")

    def extra(self, ctx: Context, item: Item) -> None:
        for value in item.get("logo"):
            logo = ctx.resolve(value)
            if isinstance(logo, Item) and not logo.is_reference:
                if not (logo.has("url") or logo.has("contentUrl")):
                    self.report(ctx, "org/logo", "The logo ImageObject needs a url or contentUrl.", logo)
                for prop in ("width", "height"):
                    for v in logo.get(prop):
                        n = parse_number(v if not isinstance(v, Item) else v.first("value"))
                        if n is not None and n < 112:
                            self.report(
                                ctx, "org/logo", f"The logo {prop} is {n:g}px; Google needs at least 112px.", logo, prop
                            )
        for code in item.texts("iso6523Code"):
            if not re.fullmatch(r"\d{4}:\S+", code.strip()):
                self.report(
                    ctx,
                    "org/identifier",
                    f'iso6523Code "{code}" should be "ICD:identifier", e.g. "0060:123456789".',
                    item,
                    "iso6523Code",
                )
        for prop, prefix in (("duns", "0060"), ("leiCode", "0199")):
            if item.has(prop):
                self.report(
                    ctx,
                    "org/identifier",
                    f'Google deprecated "{prop}" in favour of iso6523Code with the prefix "{prefix}:".',
                    item,
                    prop,
                )
        names = item.texts("name")
        for legal in item.texts("legalName"):
            if legal in names:
                self.report(
                    ctx,
                    "org/identifier",
                    "legalName is the same as name; only set it when it differs.",
                    item,
                    "legalName",
                )
        check_self_serving(ctx, self, item)
        # Google accepts a store-wide return policy on the Organization.
        check_return_policy(ctx, item)


LOCAL_BUSINESS = LocalBusiness()
ORGANIZATION = Organization()
