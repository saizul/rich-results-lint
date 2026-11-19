"""Rule registry: every rule id with its default severity and description."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from .model import Severity

GOOGLE_DOCS = "https://developers.google.com/search/docs/appearance/structured-data/"
DOCS = "https://github.com/saizul/rich-results-lint#rule-reference"

E, W, I = Severity.ERROR, Severity.WARNING, Severity.INFO  # noqa: E741 - short names keep the table readable


@dataclass(frozen=True)
class Rule:
    id: str
    severity: Severity
    description: str
    help_uri: str = DOCS


_RULES = [
    # Syntax and extraction
    Rule("syntax/json-invalid", E, "A JSON-LD script is not valid JSON."),
    Rule("syntax/json-ld-shape", E, "A JSON-LD script holds something other than an object or an array of objects."),
    Rule("syntax/empty-script", W, "A JSON-LD script is empty."),
    Rule("syntax/missing-context", W, "A JSON-LD object has no @context, so its terms are not schema.org terms."),
    Rule("syntax/unknown-context", W, "The @context is not schema.org."),
    Rule("syntax/unknown-keyword", W, "A key starts with @ but is not a JSON-LD keyword."),
    Rule("syntax/microdata-no-type", W, "An itemscope element has no itemtype."),
    Rule("syntax/rdfa-no-vocab", W, "An RDFa typeof is used without a schema.org vocab or prefix."),
    Rule("syntax/fetch-failed", E, "The page could not be fetched or read."),
    # schema.org vocabulary
    Rule("schema/unknown-type", E, "The @type is not a schema.org type (often a typo or wrong case)."),
    Rule("schema/external-type", I, "The type comes from another vocabulary and is not checked."),
    Rule("schema/missing-type", I, "An object has no @type (reported as a warning for top-level items)."),
    Rule("schema/unknown-property", W, "The property is not a schema.org property (often a typo or wrong case)."),
    Rule("schema/unexpected-property", I, "The property exists but is not defined for this type."),
    Rule("schema/superseded-property", I, "The property is superseded in schema.org."),
    Rule("schema/invalid-enum", E, "The value is not a member of the expected schema.org enumeration."),
    # Values
    Rule("value/empty", W, "A property has an empty value."),
    Rule("value/date", E, "A date or date-time is not valid ISO 8601."),
    Rule("value/duration", E, "A duration is not a valid ISO 8601 duration (PT1H30M)."),
    Rule("value/timezone", I, "A date-time has no timezone offset."),
    Rule("value/url-relative", W, "A URL is relative; use an absolute URL."),
    Rule("value/url-invalid", E, "A URL property does not hold a URL."),
    Rule("value/price", E, "A price is not a plain number (no currency symbols, thousands separators or ranges)."),
    Rule("value/currency", E, "A currency is not a three-letter ISO 4217 code."),
    Rule("value/country", W, "A country is not a two-letter ISO 3166-1 code."),
    Rule("value/number", E, "A numeric property does not hold a number."),
    Rule("value/boolean", W, "A boolean property does not hold true or false."),
    # Graph
    Rule("graph/unresolved-id", W, "A node reference (@id) points to a node that is not defined on the page."),
    Rule("graph/duplicate-id", W, "The same @id is defined more than once with different types."),
    # Google rich results: generic
    Rule("google/required", E, "A property required for the rich result is missing.", GOOGLE_DOCS),
    Rule("google/recommended", W, "A recommended property is missing.", GOOGLE_DOCS),
    Rule("google/deprecated-feature", W, "Google no longer shows this rich result.", GOOGLE_DOCS),
    # Feature specific
    Rule("article/author", W, "Article author should be a Person or Organization with only the name in author.name."),
    Rule("article/image", W, "Article image should be a crawlable absolute URL or an ImageObject with a URL."),
    Rule("product/offer-review-or-rating", E, "A Product needs at least one of offers, review or aggregateRating."),
    Rule("product/price-zero", I, "A price of 0 means free; merchant listings need a price greater than zero."),
    Rule("product/aggregate-offer", E, "An AggregateOffer needs lowPrice and priceCurrency."),
    Rule("product/price-valid-until", W, "priceValidUntil is in the past, which can stop the snippet from showing."),
    Rule("merchant/required", W, "A property needed for merchant listing experiences is missing."),
    Rule("merchant/shipping", W, "Offer shipping details are incomplete or inconsistent."),
    Rule("merchant/return-policy", W, "A merchant return policy is incomplete or inconsistent."),
    Rule("review/rating-range", E, "A rating value is outside the bestRating and worstRating range."),
    Rule("review/author-name", W, "A review author name looks like a promotion or is too long."),
    Rule("review/item-type", W, "The reviewed item type is not one Google supports for review snippets."),
    Rule("review/self-serving", W, "Reviews of a LocalBusiness or Organization on its own site are not eligible."),
    Rule("breadcrumb/items", E, "A BreadcrumbList needs at least two ListItems."),
    Rule("breadcrumb/position", E, "ListItem positions must be integers that start at 1 and do not repeat."),
    Rule("breadcrumb/item", E, "Every ListItem except the last needs an item URL."),
    Rule("event/status", E, "eventStatus is not one of the values Google supports."),
    Rule("event/dates", E, "Event dates are inconsistent."),
    Rule("event/online-only", W, "Online-only events are not eligible for event rich results."),
    Rule("job/employment-type", E, "employmentType is not one of FULL_TIME, PART_TIME, CONTRACTOR, ..."),
    Rule("job/salary", E, "baseSalary is not a MonetaryAmount with a currency and a valid unitText."),
    Rule("job/remote", E, "Remote job markup is inconsistent."),
    Rule("job/title", W, "The job title contains codes, prices, dates or special characters."),
    Rule("job/description", E, "The job description is missing, too short or the same as the title."),
    Rule("job/expired", W, "validThrough is in the past; the job is treated as expired."),
    Rule("job/location-country", E, "jobLocation.address needs addressCountry."),
    Rule("recipe/times", W, "cookTime should come with prepTime, or use totalTime."),
    Rule("recipe/yield", W, "recipeYield is required when nutrition.calories is set."),
    Rule("recipe/instructions", W, "recipeInstructions should be HowToStep items with text."),
    Rule("video/clips", E, "Clip markup is incomplete or has duplicate start offsets."),
    Rule("video/regions", W, "Use either regionsAllowed or ineligibleRegion, not both."),
    Rule("video/expired", W, "The video's expires date is in the past."),
    Rule("video/live", E, "A live BroadcastEvent needs isLiveBroadcast and startDate."),
    Rule("local/geo", W, "Latitude and longitude should have at least five decimal places."),
    Rule("local/opening-hours", E, "openingHoursSpecification has an invalid day or time."),
    Rule("local/telephone", W, "The telephone number should include the country code (+880...)."),
    Rule("local/price-range", W, "priceRange should be shorter than 100 characters."),
    Rule("org/logo", W, "The logo should be at least 112x112 pixels and have a URL."),
    Rule("org/identifier", I, "An Organization identifier is deprecated or malformed."),
    Rule("software/rating", E, "A software app needs aggregateRating or review."),
    Rule("software/category", W, "applicationCategory is not one of the categories Google supports."),
    Rule("software/video-game", E, "A VideoGame must be co-typed with SoftwareApplication."),
    Rule("dataset/description", E, "The dataset description is not 50 to 5000 characters or repeats the name."),
    Rule("dataset/distribution", E, "A distribution is not a DataDownload with a contentUrl."),
    Rule("dataset/temporal-coverage", E, "temporalCoverage is not an ISO 8601 date or interval."),
    Rule("dataset/creator", W, "The dataset creator should be a Person or Organization."),
    Rule("dataset/license", I, "A dataset that is not free to access has no license."),
    Rule("profile/main-entity", E, "A ProfilePage mainEntity must be one Person or Organization."),
    Rule("profile/interaction", W, "An interaction statistic is not an InteractionCounter with a supported type."),
    Rule("profile/dates", W, "Profile page dates are inconsistent."),
    Rule("forum/author", W, "A forum post author should be a Person with a name, not text."),
    Rule("forum/dates", W, "Forum post dates are inconsistent or in the future."),
    Rule("faq/structure", W, "An FAQPage question is missing its name or accepted answer text."),
    # Content hints
    Rule("content/not-visible", I, "Marked-up text does not appear in the visible page text."),
    Rule("content/price-mismatch", I, "The marked-up price does not appear in the visible page text."),
    Rule("content/no-structured-data", I, "No structured data was found."),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}


def get_rule(rule_id: str) -> Rule:
    return RULES[rule_id]


def matches(rule_id: str, patterns: list[str]) -> bool:
    """True when a rule id matches any pattern: an exact id, a group (``value``), or a glob (``google/*``)."""
    for p in patterns:
        p = p.strip()
        if not p:
            continue
        if rule_id == p or rule_id.startswith(p.rstrip("/") + "/") or fnmatch.fnmatchcase(rule_id, p):
            return True
    return False
