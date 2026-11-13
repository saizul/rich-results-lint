from __future__ import annotations

import json

from .conftest import lint, page, rules


def product(name: str, price: object, body: str):
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "offers": {"@type": "Offer", "price": price, "priceCurrency": "BDT"},
    }
    return lint(page(json.dumps(data), body))


def test_visible_name_and_price_pass() -> None:
    doc = product("Nakshi Kantha", "2500", "<h1>Nakshi  Kantha</h1><p>৳ 2,500</p>")
    assert not {"content/not-visible", "content/price-mismatch"} & rules(doc)


def test_name_case_and_punctuation_are_ignored() -> None:
    doc = product("Men's Panjabi - Blue", 1500, "<h1>MENS PANJABI BLUE</h1><span>1500.00</span>")
    assert not {"content/not-visible", "content/price-mismatch"} & rules(doc)


def test_hidden_text_does_not_count() -> None:
    doc = product("Secret Product", 999, '<div style="display:none">Secret Product 999</div><p>Other</p>')
    assert {"content/not-visible", "content/price-mismatch"} <= rules(doc)


def test_text_only_in_script_does_not_count() -> None:
    doc = product("Only In Markup", 10, "<p>Nothing</p>")
    assert "content/not-visible" in rules(doc)


def test_content_checks_can_be_disabled() -> None:
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Gone",
        "offers": {"@type": "Offer", "price": 5, "priceCurrency": "BDT"},
    }
    doc = lint(page(json.dumps(data), "<p>x</p>"), content_checks=False)
    assert not {"content/not-visible", "content/price-mismatch"} & rules(doc)


def test_decimal_prices() -> None:
    doc = product("Tea", "12.50", "<h1>Tea</h1><p>Price 12.5</p>")
    assert "content/price-mismatch" not in rules(doc)


def test_headline_of_article() -> None:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Monsoon arrives early this year in Sylhet",
    }
    assert "content/not-visible" not in rules(
        lint(page(json.dumps(data), "<h1>Monsoon arrives early this year in Sylhet</h1>"))
    )
    assert "content/not-visible" in rules(lint(page(json.dumps(data), "<h1>Weather</h1>")))


def test_bare_jsonld_has_no_content_hints() -> None:
    from .conftest import lint_ld

    doc = lint_ld(json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": "Not on any page"}))
    assert "content/not-visible" not in rules(doc)
