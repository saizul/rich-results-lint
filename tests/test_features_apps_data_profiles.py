"""Software app, Dataset, Profile page and Discussion forum features."""

from __future__ import annotations

import json

import pytest

from rich_results_lint import Severity
from rich_results_lint.checks.features import FEATURES_BY_ID
from rich_results_lint.checks.features.dataset import temporal_problem
from rich_results_lint.cli import main

from .conftest import FIXTURES, lint, messages, page, rules


def ld(**data) -> str:
    return page(json.dumps({"@context": "https://schema.org", **data}))


def errors(doc) -> list[str]:
    return [f"{f.rule}: {f.message}" for f in doc.findings if f.severity is Severity.ERROR]


RATING = {"@type": "AggregateRating", "ratingValue": "4.5", "ratingCount": "20"}


# Software app ----------------------------------------------------------------------------------------------------


def app(**kw) -> dict:
    data = {
        "@type": "SoftwareApplication",
        "name": "App",
        "operatingSystem": "Android",
        "applicationCategory": "UtilitiesApplication",
        "offers": {"@type": "Offer", "price": "0"},
        "aggregateRating": RATING,
    }
    data.update(kw)
    return {k: v for k, v in data.items() if v is not None}


def test_features_are_registered() -> None:
    for fid in ("software-app", "dataset", "profile-page", "discussion-forum"):
        assert fid in FEATURES_BY_ID


def test_free_app_without_currency_is_eligible() -> None:
    doc = lint(ld(**app()))
    assert not errors(doc)
    assert not [f for f in doc.findings if f.feature == "Software app"]


@pytest.mark.parametrize("subtype", ["MobileApplication", "WebApplication"])
def test_subtypes_are_checked(subtype: str) -> None:
    doc = lint(ld(**app(**{"@type": subtype, "aggregateRating": None})))
    assert "software/rating" in rules(doc)


def test_paid_app_needs_currency() -> None:
    doc = lint(ld(**app(offers={"@type": "Offer", "price": "2.99"})))
    assert any("priceCurrency" in m for m in messages(doc, "google/required"))
    doc = lint(ld(**app(offers={"@type": "Offer", "price": "2.99", "priceCurrency": "USD"})))
    assert not errors(doc)


def test_app_needs_offer_price() -> None:
    doc = lint(ld(**app(offers=None)))
    assert any('"offers"' in m for m in messages(doc, "google/required"))
    doc = lint(ld(**app(offers={"@type": "Offer", "priceCurrency": "USD"})))
    assert any('"offers.price"' in m for m in messages(doc, "google/required"))


def test_app_review_counts_as_rating() -> None:
    review = {
        "@type": "Review",
        "author": {"@type": "Person", "name": "A"},
        "reviewRating": {"@type": "Rating", "ratingValue": 9},
    }
    doc = lint(ld(**app(aggregateRating=None, review=review)))
    assert "software/rating" not in rules(doc)
    # The nested review is checked as a review snippet: 9 is outside the default 1 to 5 scale.
    assert "review/rating-range" in rules(doc)


@pytest.mark.parametrize(
    ("category", "hint"),
    [
        ("Game", "GameApplication"),
        ("businessapplication", "BusinessApplication"),
        ("Developer Tools", None),
    ],
)
def test_category_suggestions(category: str, hint: str | None) -> None:
    doc = lint(ld(**app(applicationCategory=category)))
    found = messages(doc, "software/category")
    assert len(found) == 1
    if hint:
        assert f'Did you mean "{hint}"' in found[0]
    else:
        assert "Did you mean" not in found[0]


def test_category_as_schema_url() -> None:
    doc = lint(ld(**app(applicationCategory="https://schema.org/GameApplication")))
    assert "software/category" not in rules(doc)


def test_video_game_needs_co_type() -> None:
    doc = lint(ld(**app(**{"@type": "VideoGame"})))
    assert "software/video-game" in rules(doc)
    doc = lint(ld(**app(**{"@type": ["VideoGame", "SoftwareApplication"]})))
    assert "software/video-game" not in rules(doc)
    assert not errors(doc)


def test_app_in_microdata() -> None:
    html = """<html><body><div itemscope itemtype="https://schema.org/WebApplication">
      <span itemprop="name">Calc</span><meta itemprop="operatingSystem" content="All">
      <meta itemprop="applicationCategory" content="UtilitiesApplication">
      <div itemprop="offers" itemscope itemtype="https://schema.org/Offer"><meta itemprop="price" content="0"></div>
      <div itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
        <span itemprop="ratingValue">4</span> <span itemprop="ratingCount">8</span></div>
    </div></body></html>"""
    assert not errors(lint(html))


# Dataset ---------------------------------------------------------------------------------------------------------

DESCRIPTION = "Monthly retail prices of rice, lentils and onions in Dhaka markets since 2010."


def dataset(**kw) -> dict:
    data = {
        "@type": "Dataset",
        "name": "Market prices",
        "description": DESCRIPTION,
        "url": "https://example.com/prices",
        "keywords": "prices",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Organization", "name": "Lab"},
        "temporalCoverage": "2010/..",
        "distribution": {"@type": "DataDownload", "contentUrl": "https://example.com/p.csv", "encodingFormat": "CSV"},
    }
    data.update(kw)
    return {k: v for k, v in data.items() if v is not None}


def test_complete_dataset_is_clean() -> None:
    doc = lint(ld(**dataset()))
    assert not [f for f in doc.findings if f.severity.rank >= Severity.WARNING.rank]


def test_dataset_description_length() -> None:
    assert "dataset/description" in rules(lint(ld(**dataset(description="Too short."))))
    assert "dataset/description" in rules(lint(ld(**dataset(description="x" * 5001))))
    assert "dataset/description" not in rules(lint(ld(**dataset(description="x" * 5000))))


def test_dataset_distribution_needs_content_url() -> None:
    doc = lint(ld(**dataset(distribution={"@type": "DataDownload", "encodingFormat": "CSV"})))
    assert any("contentUrl" in m for m in messages(doc, "dataset/distribution"))


def test_dataset_catalog_needs_name() -> None:
    doc = lint(ld(**dataset(includedInDataCatalog={"@type": "DataCatalog"})))
    assert any("DataCatalog" in m for m in messages(doc, "google/recommended"))


def test_dataset_spatial_coverage_satisfies_coverage() -> None:
    doc = lint(ld(**dataset(temporalCoverage=None, spatialCoverage="Dhaka")))
    assert not any("Coverage" in m for m in messages(doc, "google/recommended"))
    doc = lint(ld(**dataset(temporalCoverage=None)))
    assert any("temporalCoverage" in m for m in messages(doc, "google/recommended"))


@pytest.mark.parametrize(
    "value",
    [
        "2008",
        "2008-01",
        "2008-01-15",
        "2011-11-15T10:00:00+06:00",
        "2008/2012",
        "2010-01/2010-12",
        "2013-09-01/..",
        "../2020",
    ],
)
def test_temporal_coverage_valid(value: str) -> None:
    assert temporal_problem(value) is None


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        ("", "empty"),
        ("../..", "two open ends"),
        ("2012/2008", "ends before"),
        ("2008/next year", "next year"),
        ("since 2008", "ISO 8601"),
        ("13/05/2020", "ISO 8601"),
    ],
)
def test_temporal_coverage_invalid(value: str, problem: str) -> None:
    found = temporal_problem(value)
    assert found is not None and problem in found


# Profile page ----------------------------------------------------------------------------------------------------


def test_profile_page_minimal() -> None:
    doc = lint(ld(**{"@type": "ProfilePage", "mainEntity": {"@type": "Person", "alternateName": "handle"}}))
    assert not errors(doc)


def test_profile_page_requires_main_entity() -> None:
    doc = lint(ld(**{"@type": "ProfilePage", "name": "Profile"}))
    assert any('"mainEntity"' in m for m in messages(doc, "google/required"))


def test_profile_page_main_entity_by_reference() -> None:
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "ProfilePage", "@id": "#page", "mainEntity": {"@id": "#me"}},
            {"@type": "Organization", "@id": "#me", "name": "Example Ltd"},
        ],
    }
    doc = lint(page(json.dumps(graph)))
    assert "profile/main-entity" not in rules(doc)
    assert not any("mainEntity.name" in m for m in messages(doc, "google/required"))


def test_profile_page_one_entity() -> None:
    people = [{"@type": "Person", "name": "A"}, {"@type": "Person", "name": "B"}]
    doc = lint(ld(**{"@type": "ProfilePage", "mainEntity": people}))
    assert any("one person" in m for m in messages(doc, "profile/main-entity"))


def test_interaction_statistic_must_be_counter() -> None:
    person = {"@type": "Person", "name": "A", "interactionStatistic": "412 followers"}
    doc = lint(ld(**{"@type": "ProfilePage", "mainEntity": person}))
    assert "profile/interaction" in rules(doc)


# Discussion forum ------------------------------------------------------------------------------------------------


def post(**kw) -> dict:
    data = {
        "@type": "DiscussionForumPosting",
        "headline": "Q",
        "text": "Question text",
        "url": "https://example.com/t/1",
        "datePublished": "2026-11-01T10:00:00+06:00",
        "dateModified": "2026-11-01T11:00:00+06:00",
        "author": {"@type": "Person", "name": "a", "url": "https://example.com/u/a"},
        "comment": {
            "@type": "Comment",
            "text": "Answer",
            "datePublished": "2026-11-01T12:00:00+06:00",
            "author": {"@type": "Person", "name": "b"},
        },
    }
    data.update(kw)
    return {k: v for k, v in data.items() if v is not None}


def test_forum_post_is_clean_and_not_an_article() -> None:
    doc = lint(ld(**post()))
    assert not [f for f in doc.findings if f.severity.rank >= Severity.WARNING.rank]
    # DiscussionForumPosting is an Article subtype, but the Article feature does not apply to it.
    assert not [f for f in doc.findings if f.feature == "Article"]


def test_forum_post_with_image_instead_of_text() -> None:
    doc = lint(ld(**post(text=None, image="https://example.com/i.jpg")))
    assert not errors(doc)


def test_forum_post_needs_content() -> None:
    doc = lint(ld(**post(text=None)))
    assert any('"text" or "image" or "video"' in m for m in messages(doc, "google/required"))


def test_forum_dates() -> None:
    doc = lint(ld(**post(dateModified="2026-10-01T10:00:00+06:00")))
    assert any("before datePublished" in m for m in messages(doc, "forum/dates"))


def test_nested_replies_are_checked() -> None:
    deep = {"@type": "Comment", "text": "r2", "datePublished": "2026-11-01T13:00:00+06:00"}
    reply = {
        "@type": "Comment",
        "text": "r1",
        "datePublished": "2026-11-01T12:00:00+06:00",
        "author": {"@type": "Person", "name": "b"},
        "comment": deep,
    }
    doc = lint(ld(**post(comment=reply)))
    assert any("a Comment" in m and '"author"' in m for m in messages(doc, "google/required"))


def test_social_media_posting_is_still_an_article() -> None:
    doc = lint(ld(**{"@type": "SocialMediaPosting", "headline": "Hi"}))
    assert any(f.feature == "Article" for f in doc.findings)


# CLI -------------------------------------------------------------------------------------------------------------


def test_cli_lists_and_filters_new_features(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--no-config", "--list-features"]) == 0
    out = capsys.readouterr().out
    for fid in ("software-app", "dataset", "profile-page", "discussion-forum"):
        assert fid in out
    path = str(FIXTURES / "invalid" / "software-app.html")
    assert main(["--no-config", "-f", "json", "--feature", "dataset", "--fail-on", "never", path]) == 0
    data = json.loads(capsys.readouterr().out)
    assert not any(f["rule"].startswith("software/") for d in data["documents"] for f in d["findings"])
