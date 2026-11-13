from __future__ import annotations

import json

import pytest

from rich_results_lint import Severity

from .conftest import lint, lint_ld, messages, page, rules


def thing(**data) -> str:
    return page(json.dumps({"@context": "https://schema.org", **data}))


def test_unknown_type_with_case_suggestion() -> None:
    doc = lint(thing(**{"@type": "localBusiness", "name": "x"}))
    assert any('Did you mean "LocalBusiness"' in m for m in messages(doc, "schema/unknown-type"))


def test_external_types_are_not_flagged_as_unknown() -> None:
    doc = lint(
        thing(
            **{
                "@type": ["Product", "http://purl.org/goodrelations/v1#Individual"],
                "name": "x",
                "offers": {"@type": "Offer", "price": 1, "priceCurrency": "BDT"},
            }
        )
    )
    assert "schema/unknown-type" not in rules(doc)
    assert "schema/external-type" in rules(doc)


def test_unknown_property_suggestions() -> None:
    doc = lint(
        thing(**{"@type": "Offer", "pricecurrency": "BDT", "price": 5, "availabilty": "https://schema.org/InStock"})
    )
    msgs = messages(doc, "schema/unknown-property")
    assert any('"priceCurrency"' in m for m in msgs)
    assert any('"availability"' in m for m in msgs)


def test_prefixed_and_extension_properties_are_skipped() -> None:
    doc = lint(thing(**{"@type": "Thing", "name": "n", "og:title": "x", "http://example.org/p": 1}))
    assert "schema/unknown-property" not in rules(doc)


def test_unexpected_property_only_for_known_types() -> None:
    doc = lint(thing(**{"@type": "Offer", "price": 1, "priceCurrency": "BDT", "headline": "h"}))
    assert any('"headline"' in m for m in messages(doc, "schema/unexpected-property"))
    doc = lint(thing(**{"@type": ["Offer", "MadeUpType"], "headline": "h"}))
    assert "schema/unexpected-property" not in rules(doc)


def test_superseded_property() -> None:
    doc = lint(thing(**{"@type": "Recipe", "name": "r", "ingredients": ["salt"]}))
    assert any('"recipeIngredient"' in m for m in messages(doc, "schema/superseded-property"))


def test_missing_type_top_level_is_warning_nested_is_info() -> None:
    doc = lint(thing(**{"name": "untyped"}))
    assert [f.severity for f in doc.findings if f.rule == "schema/missing-type"] == [Severity.WARNING]
    doc = lint(thing(**{"@type": "Event", "name": "e", "location": {"name": "Hall"}}))
    assert [f.severity for f in doc.findings if f.rule == "schema/missing-type"] == [Severity.INFO]


@pytest.mark.parametrize(
    ("prop", "value", "rule"),
    [
        ("datePublished", "yesterday", "value/date"),
        ("datePublished", "2026-02-30", "value/date"),
        ("dateModified", "2026-01-01T10:00:00", "value/timezone"),
        ("timeRequired", "two hours", "value/duration"),
        ("url", "page.html", "value/url-relative"),
        ("url", "https://e.com/a b", "value/url-invalid"),
        ("thumbnailUrl", "/t.jpg", "value/url-relative"),
        ("isAccessibleForFree", "yes", "value/boolean"),
        ("copyrightYear", "MMXXVI", "value/number"),
        ("name", "", "value/empty"),
        ("name", None, "value/empty"),
    ],
)
def test_value_rules(prop: str, value: object, rule: str) -> None:
    doc = lint(thing(**{"@type": "CreativeWork", prop: value}))
    assert rule in rules(doc)


@pytest.mark.parametrize(
    ("prop", "value"),
    [
        ("datePublished", "2026-01-01"),
        ("dateModified", "2026-01-01T10:00:00+06:00"),
        ("timeRequired", "PT2H"),
        ("url", "https://e.com/a"),
        ("isAccessibleForFree", True),
        ("isAccessibleForFree", "False"),
        ("copyrightYear", 2026),
        ("copyrightYear", "2026"),
        ("keywords", "a, b, c"),
    ],
)
def test_valid_values(prop: str, value: object) -> None:
    doc = lint(thing(**{"@type": "CreativeWork", prop: value}))
    assert not [r for r in rules(doc) if r.startswith("value/")]


def test_relative_url_message_mentions_page_url() -> None:
    doc = lint(thing(**{"@type": "CreativeWork", "url": "/a"}), url="https://shop.example/x")
    assert any("https://shop.example/x" in m for m in messages(doc, "value/url-relative"))


def test_microdata_relative_links_are_fine() -> None:
    html = '<div itemscope itemtype="https://schema.org/CreativeWork"><a itemprop="url" href="/a">a</a></div>'
    assert "value/url-relative" not in rules(lint(html))


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("https://schema.org/InStock", True),
        ("http://schema.org/OutOfStock", True),
        ("InStock", True),
        ("schema:PreOrder", True),
        ("In Stock", False),
        ("available", False),
        ("https://schema.org/NewCondition", False),
    ],
)
def test_enumeration_values(value: str, ok: bool) -> None:
    doc = lint(thing(**{"@type": "Offer", "price": 1, "priceCurrency": "BDT", "availability": value}))
    assert ("schema/invalid-enum" not in rules(doc)) is ok


def test_currency_and_country_suggestions() -> None:
    doc = lint(thing(**{"@type": "Offer", "price": 1, "priceCurrency": "bdt"}))
    assert any('Did you mean "BDT"' in m for m in messages(doc, "value/currency"))
    doc = lint(thing(**{"@type": "PostalAddress", "addressCountry": "bd"}))
    assert any('Did you mean "BD"' in m for m in messages(doc, "value/country"))


def test_graph_checks() -> None:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "@id": "#page", "about": {"@id": "#missing"}, "isPartOf": {"@id": "#site"}},
            {"@type": "WebSite", "@id": "#site", "name": "s"},
            {"@type": "Person", "@id": "#page"},
        ],
    }
    doc = lint(page(json.dumps(data)))
    assert any("#missing" in m for m in messages(doc, "graph/unresolved-id"))
    assert not any("#site" in m for m in messages(doc, "graph/unresolved-id"))
    assert any("#page" in m for m in messages(doc, "graph/duplicate-id"))


def test_ids_across_scripts_resolve() -> None:
    html = (
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","@id":"#o","name":"O"}</script>'
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"W","publisher":{"@id":"#o"}}</script>'
    )
    assert "graph/unresolved-id" not in rules(lint(html))


def test_bare_jsonld_document() -> None:
    doc = lint_ld('{"@context": "https://schema.org", "@type": "Product", "name": "P"}')
    assert doc.items[0].types == ["Product"]
    assert "product/offer-review-or-rating" in rules(doc)


def test_select_ignore_and_severity_patterns() -> None:
    html = thing(**{"@type": "Product", "descripton": "x", "image": "/i.jpg"})
    assert rules(lint(html, select=["schema"])) == {"schema/unknown-property"}
    assert "value/url-relative" not in rules(lint(html, ignore=["value/*"]))
    doc = lint(html, severity={"schema/unknown-property": "error"})
    assert [f.severity for f in doc.findings if f.rule == "schema/unknown-property"] == [Severity.ERROR]


def test_findings_are_sorted_and_unique() -> None:
    doc = lint(
        thing(
            **{
                "@type": "Product",
                "name": "P",
                "offers": [{"@type": "Offer", "price": "$1"}, {"@type": "Offer", "price": "$1"}],
            }
        )
    )
    lines = [f.line for f in doc.findings]
    assert lines == sorted(lines)
    keys = [(f.rule, f.line, f.path, f.message) for f in doc.findings]
    assert len(keys) == len(set(keys))
