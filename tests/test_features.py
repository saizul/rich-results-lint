from __future__ import annotations

import json

import pytest

from rich_results_lint import Severity

from .conftest import lint, messages, page, rules


def ld(**data) -> str:
    return page(json.dumps({"@context": "https://schema.org", **data}))


def findings_for(doc, rule):
    return [f for f in doc.findings if f.rule == rule]


# Product ---------------------------------------------------------------------------------------------------------


def test_product_minimal_snippet_is_eligible() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "review": {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": "A"},
                    "reviewRating": {"@type": "Rating", "ratingValue": 4},
                },
            }
        )
    )
    assert not [f for f in doc.findings if f.severity is Severity.ERROR]


def test_product_requires_name_and_one_of() -> None:
    doc = lint(ld(**{"@type": "Product"}))
    assert any('"name"' in m for m in messages(doc, "google/required"))
    assert "product/offer-review-or-rating" in rules(doc)


def test_offer_price_from_price_specification() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "image": "https://e.com/i.jpg",
                "offers": {
                    "@type": "Offer",
                    "priceSpecification": {"@type": "UnitPriceSpecification", "price": 10, "priceCurrency": "BDT"},
                },
            }
        )
    )
    assert not any("price" in m for m in messages(doc, "google/required"))
    assert "merchant/required" not in rules(doc)


def test_offer_without_price() -> None:
    doc = lint(ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "priceCurrency": "BDT"}}))
    assert any("price" in m for m in messages(doc, "google/required"))


def test_offers_as_text() -> None:
    doc = lint(ld(**{"@type": "Product", "name": "P", "offers": "500 taka"}))
    assert any("not text" in m for m in messages(doc, "google/required"))


def test_merchant_listing_warnings() -> None:
    doc = lint(ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "price": 10}}))
    merchant = findings_for(doc, "merchant/required")
    assert {f.message.split('"')[1] if '"' in f.message else "priceCurrency" for f in merchant} >= {"image"}
    assert all(f.severity is Severity.WARNING and f.feature == "Merchant listing" for f in merchant)


def test_merchant_severity_can_be_raised() -> None:
    doc = lint(
        ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "price": 10}}),
        severity={"merchant/*": "error"},
    )
    assert all(f.severity is Severity.ERROR for f in findings_for(doc, "merchant/required"))


@pytest.mark.parametrize("price", ["$10", "1,000", "10-20", "10,5", "ten"])
def test_bad_prices(price: str) -> None:
    doc = lint(
        ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "price": price, "priceCurrency": "BDT"}})
    )
    assert "value/price" in rules(doc)


def test_free_product_is_info() -> None:
    doc = lint(
        ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BDT"}})
    )
    f = findings_for(doc, "product/price-zero")
    assert f and f[0].severity is Severity.INFO


def test_negative_price() -> None:
    doc = lint(
        ld(**{"@type": "Product", "name": "P", "offers": {"@type": "Offer", "price": -5, "priceCurrency": "BDT"}})
    )
    assert any("negative" in m for m in messages(doc, "value/price"))


def test_product_cotyped_with_car() -> None:
    doc = lint(
        ld(
            **{
                "@type": ["Product", "Car"],
                "name": "Corolla",
                "offers": {"@type": "Offer", "price": 100, "priceCurrency": "BDT"},
            }
        )
    )
    assert "product/offer-review-or-rating" not in rules(doc)
    assert "schema/unknown-type" not in rules(doc)


def test_offer_reference_resolves_through_graph() -> None:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Product", "name": "P", "image": "https://e.com/i.jpg", "offers": {"@id": "#offer"}},
            {
                "@type": "Offer",
                "@id": "#offer",
                "price": 5,
                "priceCurrency": "BDT",
                "availability": "https://schema.org/InStock",
                "priceValidUntil": "2030-01-01",
            },
        ],
    }
    doc = lint(page(json.dumps(data)))
    assert not [f for f in doc.findings if f.severity is Severity.ERROR]
    assert "graph/unresolved-id" not in rules(doc)


# Review snippet ----------------------------------------------------------------------------------------------------


def test_review_requires_author_and_rating() -> None:
    doc = lint(ld(**{"@type": "Review", "itemReviewed": {"@type": "Book", "name": "B"}}))
    required = " ".join(messages(doc, "google/required"))
    assert '"author"' in required and '"reviewRating"' in required


def test_standalone_review_needs_item_reviewed() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Review",
                "author": {"@type": "Person", "name": "A"},
                "reviewRating": {"@type": "Rating", "ratingValue": 5},
            }
        )
    )
    assert any("itemReviewed" in m for m in messages(doc, "google/required"))


def test_nested_review_does_not_need_item_reviewed() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Recipe",
                "name": "R",
                "image": "https://e.com/r.jpg",
                "review": {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": "A"},
                    "reviewRating": {"@type": "Rating", "ratingValue": 5},
                },
            }
        )
    )
    assert not any("itemReviewed" in m for m in messages(doc, "google/required"))


@pytest.mark.parametrize(
    ("rating", "ok"),
    [
        ({"ratingValue": 5}, True),
        ({"ratingValue": 0}, False),
        ({"ratingValue": 6}, False),
        ({"ratingValue": 8, "bestRating": 10}, True),
        ({"ratingValue": 0, "bestRating": 10, "worstRating": 0}, True),
        ({"ratingValue": "85%"}, True),
        ({"ratingValue": "7/10"}, True),
        ({"ratingValue": "11/10"}, False),
        ({"ratingValue": 3, "bestRating": 3, "worstRating": 3}, False),
    ],
)
def test_rating_ranges(rating: dict, ok: bool) -> None:
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "review": {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": "A"},
                    "reviewRating": {"@type": "Rating", **rating},
                },
            }
        )
    )
    assert ("review/rating-range" not in rules(doc)) is ok


def test_aggregate_rating_counts() -> None:
    doc = lint(
        ld(**{"@type": "Product", "name": "P", "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4}})
    )
    assert any("ratingCount" in m for m in messages(doc, "google/required"))
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4, "ratingCount": 0},
            }
        )
    )
    assert "review/rating-range" in rules(doc)


def test_decimal_comma_rating_is_info() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4,4", "ratingCount": 5},
            }
        )
    )
    assert any(f.severity is Severity.INFO and "decimal comma" in f.message for f in doc.findings)


@pytest.mark.parametrize("name", ["50% off until Saturday", "Best deal https://shop.example", "x" * 120])
def test_promotional_author_names(name: str) -> None:
    doc = lint(
        ld(
            **{
                "@type": "Product",
                "name": "P",
                "review": {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": name},
                    "reviewRating": {"@type": "Rating", "ratingValue": 4},
                },
            }
        )
    )
    assert "review/author-name" in rules(doc)


def test_review_item_type() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Review",
                "itemReviewed": {"@type": "WebSite", "name": "W"},
                "author": {"@type": "Person", "name": "A"},
                "reviewRating": {"@type": "Rating", "ratingValue": 4},
            }
        )
    )
    assert "review/item-type" in rules(doc)
    doc = lint(
        ld(
            **{
                "@type": "Review",
                "itemReviewed": {"@type": "MobileApplication", "name": "App"},
                "author": {"@type": "Person", "name": "A"},
                "reviewRating": {"@type": "Rating", "ratingValue": 4},
            }
        )
    )
    assert "review/item-type" not in rules(doc)


def test_self_serving_reviews() -> None:
    for t in ("LocalBusiness", "Dentist", "Organization", "Corporation"):
        doc = lint(
            ld(
                **{
                    "@type": t,
                    "name": "N",
                    "aggregateRating": {"@type": "AggregateRating", "ratingValue": 5, "ratingCount": 10},
                }
            )
        )
        assert "review/self-serving" in rules(doc), t


# Breadcrumb ----------------------------------------------------------------------------------------------------------


def crumbs(*elements) -> str:
    return ld(**{"@type": "BreadcrumbList", "itemListElement": list(elements)})


def test_breadcrumb_ok_with_last_item_without_url() -> None:
    doc = lint(
        crumbs(
            {"@type": "ListItem", "position": 1, "name": "A", "item": "https://e.com/a"},
            {"@type": "ListItem", "position": 2, "name": "B"},
        )
    )
    assert not doc.findings


def test_breadcrumb_item_as_thing() -> None:
    doc = lint(
        crumbs(
            {"@type": "ListItem", "position": 1, "item": {"@id": "https://e.com/a", "name": "A"}},
            {"@type": "ListItem", "position": 2, "item": {"@type": "WebPage", "@id": "https://e.com/b", "name": "B"}},
        )
    )
    assert "google/required" not in rules(doc)
    assert "breadcrumb/item" not in rules(doc)


def test_breadcrumb_positions() -> None:
    doc = lint(
        crumbs(
            {"@type": "ListItem", "position": "1", "name": "A", "item": "https://e.com/a"},
            {"@type": "ListItem", "position": 3, "name": "B"},
        )
    )
    assert any("consecutive" in m for m in messages(doc, "breadcrumb/position"))
    doc = lint(
        crumbs(
            {"@type": "ListItem", "position": 1.5, "name": "A", "item": "https://e.com/a"},
            {"@type": "ListItem", "position": 2, "name": "B"},
        )
    )
    assert any("integer" in m for m in messages(doc, "breadcrumb/position"))


def test_breadcrumb_missing_item_in_middle() -> None:
    doc = lint(
        crumbs({"@type": "ListItem", "position": 1, "name": "A"}, {"@type": "ListItem", "position": 2, "name": "B"})
    )
    assert len(findings_for(doc, "breadcrumb/item")) == 1


def test_breadcrumb_wrong_element_type() -> None:
    doc = lint(
        crumbs(
            {"@type": "Thing", "position": 1, "name": "A", "item": "https://e.com"},
            {"@type": "ListItem", "position": 2, "name": "B"},
        )
    )
    assert any("ListItem" in m for m in messages(doc, "breadcrumb/items"))


# Event -----------------------------------------------------------------------------------------------------------


EVENT = {
    "@type": "Event",
    "name": "E",
    "startDate": "2030-01-01T10:00+06:00",
    "location": {
        "@type": "Place",
        "name": "Hall",
        "address": {"@type": "PostalAddress", "addressLocality": "Dhaka", "addressCountry": "BD"},
    },
}


def test_event_location_address_required() -> None:
    doc = lint(ld(**{**EVENT, "location": {"@type": "Place", "name": "Hall"}}))
    assert any("location.address" in m for m in messages(doc, "google/required"))


def test_event_rescheduled_previous_start_date() -> None:
    doc = lint(ld(**{**EVENT, "eventStatus": "https://schema.org/EventRescheduled", "previousStartDate": "2029-12-01"}))
    assert "event/dates" not in rules(doc)
    doc = lint(ld(**{**EVENT, "eventStatus": "EventScheduled", "previousStartDate": "2029-12-01"}))
    f = findings_for(doc, "event/dates")
    assert f and f[0].severity is Severity.WARNING


def test_event_mixed_location_is_not_online_only() -> None:
    doc = lint(
        ld(**{**EVENT, "location": [EVENT["location"], {"@type": "VirtualLocation", "url": "https://e.com/live"}]})
    )
    assert "event/online-only" not in rules(doc)


def test_event_subtypes_are_checked() -> None:
    doc = lint(ld(**{"@type": "SportsEvent", "name": "Match"}))
    assert any('"startDate"' in m for m in messages(doc, "google/required"))


# Job posting -----------------------------------------------------------------------------------------------------


JOB = {
    "@type": "JobPosting",
    "title": "Accountant",
    "description": "Prepare monthly accounts, VAT returns and payroll for a growing retail company in Chattogram.",
    "datePosted": "2026-11-01",
    "hiringOrganization": {
        "@type": "Organization",
        "name": "Shop",
        "sameAs": "https://e.com",
        "logo": "https://e.com/l.png",
    },
    "jobLocation": {
        "@type": "Place",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "1",
            "addressLocality": "Chattogram",
            "addressRegion": "Chattogram",
            "postalCode": "4000",
            "addressCountry": "BD",
        },
    },
}


def test_job_minimal_has_no_errors() -> None:
    doc = lint(ld(**JOB))
    assert not [f for f in doc.findings if f.severity is Severity.ERROR]


@pytest.mark.parametrize("value", ["FULL_TIME", ["PART_TIME", "INTERN"], "PER_DIEM"])
def test_job_employment_types_ok(value) -> None:
    assert "job/employment-type" not in rules(lint(ld(**JOB, employmentType=value)))


def test_job_employment_type_suggestion() -> None:
    doc = lint(ld(**JOB, employmentType="full time"))
    assert any('Use "FULL_TIME"' in m for m in messages(doc, "job/employment-type"))


def test_job_salary_variants() -> None:
    ok = {
        "@type": "MonetaryAmount",
        "currency": "BDT",
        "value": {"@type": "QuantitativeValue", "value": 50000, "unitText": "MONTH"},
    }
    assert "job/salary" not in rules(lint(ld(**JOB, baseSalary=ok)))
    bad = {"@type": "MonetaryAmount", "value": {"@type": "QuantitativeValue", "value": 50000}}
    msgs = messages(lint(ld(**JOB, baseSalary=bad)), "job/salary")
    assert any("currency" in m for m in msgs) and any("unitText" in m for m in msgs)


def test_job_expiry_uses_clock() -> None:
    assert "job/expired" in rules(lint(ld(**JOB, validThrough="2026-11-01")))
    assert "job/expired" not in rules(lint(ld(**JOB, validThrough="2026-12-01")))


def test_job_validthrough_before_dateposted() -> None:
    doc = lint(ld(**{**JOB, "datePosted": "2026-11-10", "validThrough": "2026-11-05"}))
    assert any("before datePosted" in m for m in messages(doc, "job/expired"))


def test_remote_job_needs_country() -> None:
    job = {k: v for k, v in JOB.items() if k != "jobLocation"}
    doc = lint(ld(**job, jobLocationType="TELECOMMUTE"))
    assert "job/remote" in rules(doc)
    doc = lint(
        ld(**job, jobLocationType="TELECOMMUTE", applicantLocationRequirements={"@type": "Country", "name": "BD"})
    )
    assert "job/remote" not in rules(doc) and "google/required" not in rules(doc)


@pytest.mark.parametrize(
    "title", ["Driver!", "Sales Rep *Urgent*", "Developer $2000", "Cashier 2026-11-01", "Clerk REF-1234"]
)
def test_job_title_noise(title: str) -> None:
    assert "job/title" in rules(lint(ld(**{**JOB, "title": title})))


def test_job_description_same_as_title() -> None:
    assert any(
        "same as title" in m for m in messages(lint(ld(**{**JOB, "description": "accountant"})), "job/description")
    )


# Recipe, video, local business, organization, article ------------------------------------------------------------


def test_recipe_requires_image() -> None:
    assert any('"image"' in m for m in messages(lint(ld(**{"@type": "Recipe", "name": "R"})), "google/required"))


def test_recipe_total_time_satisfies_times() -> None:
    doc = lint(ld(**{"@type": "Recipe", "name": "R", "image": "https://e.com/r.jpg", "totalTime": "PT30M"}))
    rec = " ".join(messages(doc, "google/recommended"))
    assert "cookTime" not in rec and "prepTime" not in rec


def test_video_requires_three_properties() -> None:
    msgs = " ".join(messages(lint(ld(**{"@type": "VideoObject"})), "google/required"))
    for prop in ("name", "thumbnailUrl", "uploadDate"):
        assert f'"{prop}"' in msgs


def test_video_content_url_is_page_url() -> None:
    doc = lint(
        ld(
            **{
                "@type": "VideoObject",
                "name": "v",
                "thumbnailUrl": "https://e.com/t.jpg",
                "uploadDate": "2026-01-01",
                "contentUrl": "https://e.com/watch/",
            }
        ),
        url="https://e.com/watch",
    )
    assert any("page URL" in m for m in messages(doc, "video/clips"))


def test_nested_video_in_article_is_checked() -> None:
    doc = lint(ld(**{"@type": "Article", "headline": "h", "video": {"@type": "VideoObject", "name": "v"}}))
    assert any('"thumbnailUrl"' in m for m in messages(doc, "google/required"))


def test_food_establishment_recommendations() -> None:
    doc = lint(
        ld(**{"@type": "Restaurant", "name": "R", "address": {"@type": "PostalAddress", "addressCountry": "BD"}})
    )
    assert any("servesCuisine" in m for m in messages(doc, "google/recommended"))
    doc = lint(ld(**{"@type": "Store", "name": "S", "address": {"@type": "PostalAddress", "addressCountry": "BD"}}))
    assert not any("servesCuisine" in m for m in messages(doc, "google/recommended"))


def test_local_business_is_not_also_checked_as_organization() -> None:
    doc = lint(ld(**{"@type": "Store", "name": "S", "address": {"@type": "PostalAddress", "addressCountry": "BD"}}))
    assert all(f.feature in ("Local business", "") for f in doc.findings)


def test_opening_hours_overnight_and_closed() -> None:
    hours = [
        {"@type": "OpeningHoursSpecification", "dayOfWeek": "Friday", "opens": "18:00", "closes": "03:00"},
        {"@type": "OpeningHoursSpecification", "dayOfWeek": "Saturday", "opens": "00:00", "closes": "00:00"},
        {"@type": "OpeningHoursSpecification", "dayOfWeek": "Sunday", "opens": "00:00", "closes": "23:59"},
    ]
    doc = lint(
        ld(
            **{
                "@type": "Store",
                "name": "S",
                "address": {"@type": "PostalAddress", "addressCountry": "BD"},
                "openingHoursSpecification": hours,
            }
        )
    )
    assert "local/opening-hours" not in rules(doc)


def test_organization_logo_url_string_ok() -> None:
    doc = lint(
        ld(
            **{
                "@type": "Organization",
                "name": "O",
                "url": "https://e.com",
                "logo": "https://e.com/logo.png",
                "sameAs": "https://x.com/o",
                "address": {"@type": "PostalAddress", "addressCountry": "BD"},
                "email": "a@e.com",
            }
        )
    )
    assert not doc.findings


def test_article_has_no_required_properties() -> None:
    doc = lint(ld(**{"@type": "Article"}))
    assert "google/required" not in rules(doc)
    assert len(findings_for(doc, "google/recommended")) >= 4


def test_feature_filter() -> None:
    html = ld(**{"@type": "Product"})
    assert "google/required" not in rules(lint(html, features=["article"]))
    assert "google/required" in rules(lint(html, features=["product"]))


def test_unknown_feature_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown feature"):
        lint("", features=["nope"])
