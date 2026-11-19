"""Merchant listing details: shipping (OfferShippingDetails) and return policies (MerchantReturnPolicy).

Based on https://developers.google.com/search/docs/appearance/structured-data/merchant-listing and
https://developers.google.com/search/docs/appearance/structured-data/return-policy. Problems are reported as
warnings, like the other merchant listing checks: a page may only want product snippets.
"""

from __future__ import annotations

from ...model import Item
from ...values import parse_number, parse_price
from ..base import Context, text_of

FEATURE = "Merchant listing"
SHIPPING_DOC = "merchant-listing#shipping-details-properties"
RETURN_DOC = "return-policy"

RETURN_CATEGORIES = (
    "MerchantReturnFiniteReturnWindow",
    "MerchantReturnNotPermitted",
    "MerchantReturnUnlimitedWindow",
    "MerchantReturnUnspecified",
)
DAY_UNITS = ("DAY", "D", "d")


def enum_name(value: object) -> str:
    """``https://schema.org/ReturnByMail`` and ``schema:ReturnByMail`` become ``ReturnByMail``."""
    text = (text_of(value) or "").strip()
    for sep in ("/", ":"):
        if sep in text:
            text = text.rsplit(sep, 1)[1]
    return text


def _report(ctx: Context, rule: str, message: str, item: Item, prop: str | None, doc_page: str) -> None:
    ctx.report(rule, message, item=item, prop=prop, feature=FEATURE, doc_page=doc_page)


def check_shipping(ctx: Context, offer: Item) -> None:
    for details in ctx.items_of(offer, "shippingDetails"):
        _check_shipping_details(ctx, details)


def _check_shipping_details(ctx: Context, details: Item) -> None:
    rule = "merchant/shipping"
    rates = ctx.items_of(details, "shippingRate")
    if not details.has("shippingRate"):
        _report(ctx, rule, "OfferShippingDetails has no shippingRate.", details, None, SHIPPING_DOC)
    for rate in rates:
        has_value = rate.has("value") or rate.has("maxValue")
        if not has_value:
            _report(ctx, rule, "shippingRate needs a value (use 0 for free shipping).", rate, None, SHIPPING_DOC)
        for prop in ("value", "maxValue"):
            for raw in rate.get(prop):
                if isinstance(raw, Item):
                    continue
                amount, problem = parse_price(raw)
                if problem is None and amount is not None and amount < 0:
                    _report(ctx, rule, f"shippingRate {prop} is negative.", rate, prop, SHIPPING_DOC)
        if has_value and not rate.has("currency"):
            _report(ctx, rule, "shippingRate needs a currency (ISO 4217, e.g. BDT).", rate, None, SHIPPING_DOC)
    destinations = ctx.items_of(details, "shippingDestination")
    if not details.has("shippingDestination"):
        _report(ctx, rule, "OfferShippingDetails has no shippingDestination.", details, None, SHIPPING_DOC)
    for dest in destinations:
        if not dest.has("addressCountry"):
            _report(
                ctx,
                rule,
                "shippingDestination needs addressCountry (a two-letter ISO 3166-1 code).",
                dest,
                None,
                SHIPPING_DOC,
            )
    for delivery in ctx.items_of(details, "deliveryTime"):
        for prop in ("handlingTime", "transitTime"):
            for span in ctx.items_of(delivery, prop):
                _check_day_range(ctx, span, prop)


def _check_day_range(ctx: Context, span: Item, prop: str) -> None:
    rule = "merchant/shipping"
    low = [parse_number(v) for v in span.get("minValue")]
    high = [parse_number(v) for v in span.get("maxValue")]
    if not low and not high:
        _report(ctx, rule, f"{prop} needs minValue and maxValue (days).", span, None, SHIPPING_DOC)
        return
    for name, values in (("minValue", span.get("minValue")), ("maxValue", span.get("maxValue"))):
        for raw in values:
            n = parse_number(raw)
            if n is None or n < 0 or n != int(n):
                _report(
                    ctx, rule, f"{prop}.{name} must be a whole number of days, not {raw!r}.", span, name, SHIPPING_DOC
                )
    lo = next((n for n in low if n is not None), None)
    hi = next((n for n in high if n is not None), None)
    if lo is not None and hi is not None and lo > hi:
        _report(
            ctx, rule, f"{prop}.minValue ({lo:g}) is greater than maxValue ({hi:g}).", span, "minValue", SHIPPING_DOC
        )
    for raw in span.get("unitCode"):
        unit = text_of(raw)
        if unit is not None and unit.strip() not in DAY_UNITS:
            _report(ctx, rule, f'{prop}.unitCode "{unit}" should be DAY (or d).', span, "unitCode", SHIPPING_DOC)


def check_return_policy(ctx: Context, owner: Item) -> None:
    for policy in ctx.items_of(owner, "hasMerchantReturnPolicy"):
        _check_policy(ctx, policy)


def _check_policy(ctx: Context, policy: Item) -> None:
    rule = "merchant/return-policy"
    if policy.has("merchantReturnLink") and not policy.has("returnPolicyCategory"):
        return  # A link to the policy page alone is accepted for organization-level policies.
    categories = [enum_name(v) for v in policy.get("returnPolicyCategory")]
    if not categories:
        _report(
            ctx,
            rule,
            "MerchantReturnPolicy needs returnPolicyCategory (for example MerchantReturnFiniteReturnWindow).",
            policy,
            None,
            RETURN_DOC,
        )
    if not policy.has("applicableCountry"):
        _report(
            ctx,
            rule,
            "MerchantReturnPolicy needs applicableCountry (two-letter ISO 3166-1 codes).",
            policy,
            None,
            RETURN_DOC,
        )
    category = categories[0] if categories else ""
    if category and category not in RETURN_CATEGORIES:
        return  # Reported by schema/invalid-enum.
    if category == "MerchantReturnFiniteReturnWindow" and not policy.has("merchantReturnDays"):
        _report(
            ctx,
            rule,
            "A finite return window needs merchantReturnDays.",
            policy,
            None,
            RETURN_DOC,
        )
    for raw in policy.get("merchantReturnDays"):
        if isinstance(raw, Item):
            continue
        n = parse_number(raw)
        if n is None or n < 0 or n != int(n):
            _report(
                ctx,
                rule,
                f"merchantReturnDays must be a whole number of days, not {raw!r}.",
                policy,
                "merchantReturnDays",
                RETURN_DOC,
            )
    if category == "MerchantReturnNotPermitted":
        extra = [p for p in ("merchantReturnDays", "returnMethod", "returnFees") if policy.has(p)]
        if extra:
            _report(
                ctx,
                rule,
                f"Returns are not permitted, so {', '.join(extra)} should be removed.",
                policy,
                extra[0],
                RETURN_DOC,
            )
        return
    if category in ("MerchantReturnFiniteReturnWindow", "MerchantReturnUnlimitedWindow"):
        if not policy.has("returnMethod"):
            _report(
                ctx,
                rule,
                "Add returnMethod (ReturnByMail, ReturnInStore or ReturnAtKiosk).",
                policy,
                None,
                RETURN_DOC,
            )
        fees = [enum_name(v) for v in policy.get("returnFees")]
        if not fees:
            _report(
                ctx,
                rule,
                "Add returnFees (FreeReturn, ReturnFeesCustomerResponsibility or ReturnShippingFees).",
                policy,
                None,
                RETURN_DOC,
            )
        if "ReturnShippingFees" in fees and not policy.has("returnShippingFeesAmount"):
            _report(
                ctx,
                rule,
                "returnFees is ReturnShippingFees, so returnShippingFeesAmount is needed.",
                policy,
                "returnFees",
                RETURN_DOC,
            )
