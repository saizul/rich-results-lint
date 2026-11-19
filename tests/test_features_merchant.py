from __future__ import annotations

import json

from rich_results_lint import Severity

from .conftest import lint, messages, page, rules


def product(offer_extra: dict) -> str:
    offer = {
        "@type": "Offer",
        "price": "1200",
        "priceCurrency": "BDT",
        "availability": "https://schema.org/InStock",
        **offer_extra,
    }
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Kurta",
        "image": "https://shop.example/kurta.jpg",
        "offers": offer,
    }
    return page(json.dumps(data))


GOOD_SHIPPING = {
    "@type": "OfferShippingDetails",
    "shippingRate": {"@type": "MonetaryAmount", "value": 60, "currency": "BDT"},
    "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "BD"},
    "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "handlingTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY"},
        "transitTime": {"@type": "QuantitativeValue", "minValue": 1, "maxValue": 3, "unitCode": "d"},
    },
}

GOOD_POLICY = {
    "@type": "MerchantReturnPolicy",
    "applicableCountry": "BD",
    "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
    "merchantReturnDays": 7,
    "returnMethod": "https://schema.org/ReturnByMail",
    "returnFees": "https://schema.org/FreeReturn",
}


def test_complete_shipping_and_return_policy_are_clean() -> None:
    doc = lint(product({"shippingDetails": GOOD_SHIPPING, "hasMerchantReturnPolicy": GOOD_POLICY}))
    assert not {"merchant/shipping", "merchant/return-policy"} & rules(doc)


def test_shipping_details_problems() -> None:
    shipping = {
        "@type": "OfferShippingDetails",
        "shippingRate": {"@type": "MonetaryAmount", "value": -5},
        "shippingDestination": {"@type": "DefinedRegion", "addressRegion": "Dhaka"},
        "deliveryTime": {
            "@type": "ShippingDeliveryTime",
            "handlingTime": {"@type": "QuantitativeValue", "minValue": 3, "maxValue": 1, "unitCode": "HUR"},
            "transitTime": {"@type": "QuantitativeValue", "minValue": 1.5, "maxValue": 4},
        },
    }
    doc = lint(product({"shippingDetails": shipping}))
    found = messages(doc, "merchant/shipping")
    assert any("negative" in m for m in found)
    assert any("currency" in m for m in found)
    assert any("addressCountry" in m for m in found)
    assert any("greater than maxValue" in m for m in found)
    assert any('unitCode "HUR"' in m for m in found)
    assert any("whole number of days" in m for m in found)
    shipping_findings = [f for f in doc.findings if f.rule == "merchant/shipping"]
    assert all(f.severity is Severity.WARNING and f.feature == "Merchant listing" for f in shipping_findings)
    assert all("merchant-listing" in f.help_uri for f in shipping_findings)


def test_shipping_details_missing_rate_destination_and_times() -> None:
    shipping = {
        "@type": "OfferShippingDetails",
        "deliveryTime": {"@type": "ShippingDeliveryTime", "transitTime": {"@type": "QuantitativeValue"}},
    }
    found = messages(lint(product({"shippingDetails": shipping})), "merchant/shipping")
    assert any("no shippingRate" in m for m in found)
    assert any("no shippingDestination" in m for m in found)
    assert any("transitTime needs minValue and maxValue" in m for m in found)


def test_free_shipping_with_zero_rate_is_fine() -> None:
    shipping = {**GOOD_SHIPPING, "shippingRate": {"@type": "MonetaryAmount", "value": 0, "currency": "BDT"}}
    assert "merchant/shipping" not in rules(lint(product({"shippingDetails": shipping})))


def test_return_policy_problems() -> None:
    policy = {
        "@type": "MerchantReturnPolicy",
        "returnPolicyCategory": "MerchantReturnFiniteReturnWindow",
        "returnFees": "https://schema.org/ReturnShippingFees",
    }
    found = messages(lint(product({"hasMerchantReturnPolicy": policy})), "merchant/return-policy")
    assert any("applicableCountry" in m for m in found)
    assert any("merchantReturnDays" in m for m in found)
    assert any("returnMethod" in m for m in found)
    assert any("returnShippingFeesAmount" in m for m in found)
    assert not any("Add returnFees" in m for m in found)


def test_return_policy_category_and_days() -> None:
    missing = messages(
        lint(product({"hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "applicableCountry": "BD"}})),
        "merchant/return-policy",
    )
    assert any("needs returnPolicyCategory" in m for m in missing)
    bad_days = messages(
        lint(product({"hasMerchantReturnPolicy": {**GOOD_POLICY, "merchantReturnDays": "a week"}})),
        "merchant/return-policy",
    )
    assert any("whole number of days" in m for m in bad_days)


def test_no_returns_policy_should_not_list_return_details() -> None:
    policy = {
        "@type": "MerchantReturnPolicy",
        "applicableCountry": "BD",
        "returnPolicyCategory": "https://schema.org/MerchantReturnNotPermitted",
        "returnMethod": "https://schema.org/ReturnByMail",
    }
    found = messages(lint(product({"hasMerchantReturnPolicy": policy})), "merchant/return-policy")
    assert found == ["Returns are not permitted, so returnMethod should be removed."]
    clean = {k: v for k, v in policy.items() if k != "returnMethod"}
    assert "merchant/return-policy" not in rules(lint(product({"hasMerchantReturnPolicy": clean})))


def test_organization_level_return_policy() -> None:
    org = {
        "@context": "https://schema.org",
        "@type": "OnlineStore",
        "name": "Shop",
        "url": "https://shop.example/",
        "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "applicableCountry": "BD"},
    }
    assert "merchant/return-policy" in rules(lint(page(json.dumps(org))))
    link_only = {
        **org,
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "merchantReturnLink": "https://shop.example/returns",
        },
    }
    assert "merchant/return-policy" not in rules(lint(page(json.dumps(link_only))))


def test_merchant_detail_severity_can_be_raised() -> None:
    doc = lint(
        product({"shippingDetails": {"@type": "OfferShippingDetails"}}),
        severity={"merchant/*": "error"},
    )
    assert all(f.severity is Severity.ERROR for f in doc.findings if f.rule == "merchant/shipping")
