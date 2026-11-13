from __future__ import annotations

from rich_results_lint.vocab import get_vocabulary, is_schema_iri, local_name


def test_vocabulary_is_loaded() -> None:
    v = get_vocabulary()
    assert v.version
    assert len(v.types) > 800
    assert len(v.properties) > 1400
    for t in ("Product", "Offer", "Recipe", "JobPosting", "VideoObject", "BreadcrumbList", "LocalBusiness", "Event"):
        assert v.is_type(t)


def test_type_hierarchy() -> None:
    v = get_vocabulary()
    assert v.is_subtype("Restaurant", "LocalBusiness")
    assert v.is_subtype("Restaurant", "Organization")
    assert v.is_subtype("NewsArticle", "Article")
    assert v.is_subtype("Recipe", "HowTo")
    assert not v.is_subtype("Product", "CreativeWork")
    assert "Thing" in v.ancestors("Offer")


def test_properties_of_types() -> None:
    v = get_vocabulary()
    assert "price" in v.properties_of("Offer")
    assert "name" in v.properties_of("Product")
    assert v.expects(["Product"], "offers")
    assert not v.expects(["Product"], "headline")
    assert v.expects(["NotAType"], "headline")
    assert v.superseded_by("interactionCount") == "interactionStatistic"
    assert "Duration" in v.ranges("cookTime")


def test_suggestions() -> None:
    v = get_vocabulary()
    assert v.suggest_type("product") == "Product"
    assert v.suggest_type("Prodcut") == "Product"
    assert v.suggest_type("Zzzzzz") is None
    assert v.suggest_property("descripton", ["Product"]) == "description"
    assert v.suggest_property("PriceCurrency", ["Offer"]) == "priceCurrency"
    assert v.suggest_property("aggregateRatings", ["Product"]) == "aggregateRating"


def test_enumerations() -> None:
    v = get_vocabulary()
    assert "ItemAvailability" in v.enum_of("InStock")
    assert "InStock" in v.members_of("ItemAvailability")
    assert v.suggest_member("In Stock", "ItemAvailability") == "InStock"
    assert v.suggest_member("out_of_stock", "ItemAvailability") == "OutOfStock"


def test_local_name() -> None:
    assert local_name("https://schema.org/Product") == "Product"
    assert local_name("http://schema.org/Product") == "Product"
    assert local_name("schema:Product") == "Product"
    assert local_name("Product") == "Product"
    assert local_name("http://example.com/Thing") == "http://example.com/Thing"
    assert is_schema_iri("https://schema.org/")
    assert not is_schema_iri("https://example.org/")
