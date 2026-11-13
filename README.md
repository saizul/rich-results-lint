# rich-results-lint

A linter for **JSON-LD, Microdata and RDFa structured data**: schema.org typos, ISO 8601 dates and durations, URLs,
prices, `@id` references and Google's rich result requirements, with text, JSON and SARIF output.

[![CI](https://github.com/saizul/rich-results-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/saizul/rich-results-lint/actions/workflows/ci.yml)
[![Container image](https://github.com/saizul/rich-results-lint/actions/workflows/publish-image.yml/badge.svg)](https://github.com/saizul/rich-results-lint/actions/workflows/publish-image.yml)
![python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

Google's Rich Results Test checks one URL at a time in a browser. `rich-results-lint` runs the same kind of checks
on files, directories and URLs from the command line, so structured data can be tested in CI before a deploy:

```console
$ rich-results-lint product.html
product.html  (2 items: BreadcrumbList, Product)
  product.html:11: warning value/url-relative: image: "/images/jamdani.jpg" is a relative URL; use an absolute URL. [Product]
  product.html:12: warning schema/unknown-property: "descripton" is not a schema.org property. Did you mean "description"? [Product]
  product.html:13: warning graph/unresolved-id: @id "#brand" is referenced but no node with that @id is defined on the page. Google does not fetch other pages to resolve it. [@id reference]
  product.html:16: error value/price: price "৳12,500" contains a currency symbol or code; put the currency in priceCurrency. [Offer]
  product.html:17: error value/currency: priceCurrency "Tk" is not a three-letter ISO 4217 currency code (BDT, USD, EUR). [Offer]
  product.html:18: error schema/invalid-enum: availability "In Stock" is not an allowed ItemAvailability value. Use "https://schema.org/InStock". [Offer]
  product.html:19: warning product/price-valid-until: priceValidUntil 2024-12-31 is in the past; the snippet may not be shown. [Offer]
  product.html:21: error google/required: Missing required property "ratingCount" or "reviewCount" for an AggregateRating. [AggregateRating]
  product.html:21: info value/number: ratingValue "4,7" uses a decimal comma; use "4.7". [AggregateRating]
  product.html:30: error breadcrumb/position: Position 1 is followed by 3; positions should be consecutive. [ListItem]
5 errors, 4 warnings, 1 info in 1 document (2 items)
```

## Contents

- [Features](#features)
- [Install](#install)
- [Docker image](#docker-image)
- [Usage](#usage)
- [Google rich result checks](#google-rich-result-checks)
- [Rule reference](#rule-reference)
- [Configuration](#configuration)
- [Output formats and exit codes](#output-formats-and-exit-codes)
- [Python API](#python-api)
- [Examples](#examples)
- [Testing](#testing)
- [Limitations](#limitations)
- [Data and licences](#data-and-licences)
- [Contributing](#contributing)
- [License](#license)

## Features

- **All three syntaxes** - JSON-LD (`@graph`, arrays, `@id` references, `@list`, value objects, prefixed and full IRI
  terms), Microdata (`itemscope`, `itemtype`, `itemprop`, `itemid`, `itemref`) and RDFa Lite (`vocab`, `typeof`,
  `property`, `prefix`, `resource`).
- **Precise locations** - JSON-LD is parsed with a position-tracking parser, so every finding has the page line of the
  property, plus a JSON path such as `$script[0].offers.price`.
- **schema.org vocabulary** - a bundled, trimmed schema.org 30.1 vocabulary (939 types, 1,538 properties, 485
  enumeration members) catches unknown types and properties with "did you mean" suggestions, properties used on the
  wrong type, superseded properties and invalid enumeration values (`"In Stock"` instead of
  `https://schema.org/InStock`).
- **Values** - ISO 8601 dates, date-times (with calendar validation) and durations, missing timezones, relative and
  malformed URLs, price formats (currency symbols, thousands separators, ranges, decimal commas), ISO 4217 currencies,
  ISO 3166-1 country codes, numbers and booleans.
- **Graph** - `@id` references that point to nothing on the page and `@id`s defined twice with different types.
  References are resolved across scripts and `@graph`, so `"offers": {"@id": "#offer"}` is checked as an Offer.
- **Google rich results** - required and recommended properties and the documented value rules for Article, Product
  snippet and merchant listing (offers, review and aggregateRating), Breadcrumb, FAQ (deprecated), How-to (removed),
  Local business, Organization, Event, Job posting, Recipe, Video and Review snippet. See
  [Google rich result checks](#google-rich-result-checks).
- **Content mismatch hints** - names, headlines and prices in JSON-LD that do not appear in the visible page text.
- **Output** - text (with colour), JSON and SARIF 2.1.0 for GitHub code scanning; exit codes for CI.
- **Configurable** - select, ignore and re-grade rules by id, group or glob; limit to some features; settings in
  `pyproject.toml` or `.rich-results-lint.toml`.
- **Light** - one runtime dependency (`httpx`, plus `tomli` on Python 3.10). HTML parsing uses the standard library.

## Install

```bash
pip install "rich-results-lint @ git+https://github.com/saizul/rich-results-lint"
# or from a clone
git clone https://github.com/saizul/rich-results-lint.git && cd rich-results-lint && pip install .
```

Python 3.10 or newer is required.

## Docker image

A multi-arch image (linux/amd64, linux/arm64) is published to GitHub Packages:

```bash
docker pull ghcr.io/saizul/rich-results-lint:latest
docker run --rm ghcr.io/saizul/rich-results-lint:latest https://www.example.com/
docker run --rm -v "$PWD:/work" ghcr.io/saizul/rich-results-lint:latest public/ --format sarif --output report.sarif
```

Mount the folder with your files at `/work`, the working directory of the image. A `.rich-results-lint.toml` or
`pyproject.toml` in that folder is picked up. Release images are also tagged with the version
(`ghcr.io/saizul/rich-results-lint:0.1.0`) and every build with its commit SHA.

## Usage

```console
$ rich-results-lint page.html                     # one file
$ rich-results-lint public/                       # every .html, .htm, .xhtml, .json and .jsonld file below public/
$ rich-results-lint https://www.example.com/p/1   # fetch a page (redirects followed, 10 MB limit)
$ curl -s https://www.example.com/ | rich-results-lint -       # standard input (HTML or JSON-LD)
$ rich-results-lint data.jsonld                   # a bare JSON-LD document
$ rich-results-lint public/ --format sarif -o structured-data.sarif
$ rich-results-lint public/ --select google,value --ignore content --fail-on warning
$ rich-results-lint shop/ --feature product --severity merchant/required=error
$ rich-results-lint --list-rules
$ rich-results-lint --list-features
```

| Option | Description |
| --- | --- |
| `-f`, `--format text\|json\|sarif` | Output format. Default `text`. |
| `-o`, `--output FILE` | Write the report to a file. |
| `--fail-on error\|warning\|info\|never` | Lowest severity that makes the exit status 1. Default `error`. |
| `--select RULES` | Only report these rules. Comma-separated, repeatable. Ids (`value/date`), groups (`value`) or globs (`google/*`). |
| `--ignore RULES` | Do not report these rules. |
| `--severity RULE=LEVEL` | Change a rule's severity (`error`, `warning`, `info`). Patterns allowed. Repeatable. |
| `--feature ID` | Only run these Google feature checks (`product`, `recipe` ...). Schema and value checks always run. |
| `--no-content-checks` | Skip the visible-content hints. |
| `--base-url URL` | Page URL of local files, used in relative URL messages and the video page-URL check. |
| `--timeout SECONDS`, `--user-agent UA` | HTTP settings for URLs. Default 20 s and `rich-results-lint/<version>`. |
| `--config FILE`, `--no-config` | Use a specific config file, or none. |
| `--color auto\|always\|never` | Colour in text output. `NO_COLOR` is honoured. |
| `-v`, `--verbose` | List documents without findings too. |

## Google rich result checks

Requirements were verified on **2026-11-13** against the Google Search Central structured data documentation at
<https://developers.google.com/search/docs/appearance/structured-data/> (the type pages listed below, the Search
gallery and the "Latest documentation updates" changelog for deprecations). Google changes these pages; if a rule
looks out of date, please open an issue with a link to the current page.

| Feature (`--feature`) | Types (and subtypes) | Required (error) | Recommended (warning) | Extra checks |
| --- | --- | --- | --- | --- |
| Article (`article`) | Article, NewsArticle, BlogPosting | none | author, author.name, author.url or sameAs, datePublished, dateModified, headline, image | author must be Person/Organization; author.name holds only the name, one author per entry; ImageObject needs a URL |
| Product snippet (`product`) | Product (also co-typed, e.g. Product + Car) | name; one of offers, review or aggregateRating; Offer: price or priceSpecification.price; AggregateOffer: lowPrice, priceCurrency | Offer: priceCurrency, availability, priceValidUntil; AggregateOffer: highPrice, offerCount | price format, price 0 (free), past priceValidUntil, nested review and aggregateRating |
| Merchant listing | Product with offers | image, Offer priceCurrency (reported as warning `merchant/required`; raise with `--severity`) | | price must be greater than 0 |
| Review snippet (`review`) | Review, AggregateRating, and review/aggregateRating nested in any checked item | Review: author, author.name, reviewRating, reviewRating.ratingValue, itemReviewed and its name (unless nested); AggregateRating: ratingValue, ratingCount or reviewCount, itemReviewed (unless nested) | datePublished | rating within worstRating..bestRating (default 1 to 5; percentages and fractions), author name under 100 characters and not promotional, supported itemReviewed types, self-serving reviews on LocalBusiness/Organization |
| Breadcrumb (`breadcrumb`) | BreadcrumbList | itemListElement; ListItem: position, name (or a named item), item (except the last) | | at least two ListItems; integer positions starting at 1, unique and consecutive |
| FAQ (`faq`) | FAQPage | | | reported as `google/deprecated-feature`: limited to government and health sites on 2023-09-14, no longer shown from 2026-05-07, documentation removed 2026-06-15; schema.org structure (Question name, acceptedAnswer text) still checked |
| How-to (`howto`) | HowTo (not Recipe) | | | reported as `google/deprecated-feature`: removed 2023-09-14 |
| Local business (`local-business`) | LocalBusiness and subtypes (Restaurant, Store, Dentist ...) | address (a PostalAddress), name | address.streetAddress, addressLocality, postalCode, addressCountry, geo with latitude/longitude, openingHoursSpecification, telephone, url, priceRange; servesCuisine and menu for food establishments | at least 5 decimal places in coordinates, opening hours days and 24-hour times, telephone with country code, priceRange under 100 characters, self-serving reviews |
| Organization (`organization`) | Organization and subtypes except LocalBusiness | none | name, url, logo, sameAs, address, contactPoint or telephone or email | logo at least 112x112 px with a URL, iso6523Code format, deprecated duns/leiCode, legalName equal to name |
| Event (`event`) | Event and subtypes | name, startDate, location, location.address | description, endDate, eventStatus, image, location.name, offers (price, priceCurrency, availability, url, validFrom), organizer (name, url), performer (name) | eventStatus values, endDate before startDate, previousStartDate only with EventRescheduled, online-only events (not eligible since 2025-06-05) |
| Job posting (`job-posting`) | JobPosting | datePosted, description, hiringOrganization with name, jobLocation (or TELECOMMUTE with applicantLocationRequirements), title, jobLocation.address.addressCountry | baseSalary, employmentType, validThrough, directApply, identifier; hiringOrganization sameAs and logo | employmentType values (case-sensitive), baseSalary MonetaryAmount with ISO 4217 currency and unitText HOUR/DAY/WEEK/MONTH/YEAR, min not above max, title without codes/prices/dates/"!", description not equal to title, expired validThrough |
| Recipe (`recipe`) | Recipe (also in ItemList carousels) | image, name | aggregateRating, author, cookTime and prepTime (or totalTime), datePublished, description, keywords, nutrition.calories, recipeCategory, recipeCuisine, recipeIngredient, recipeInstructions, recipeYield, video | cookTime needs prepTime, recipeYield needed with calories, HowToStep/HowToSection structure, no "Step 1" labels, no single text block |
| Video (`video`) | VideoObject (also nested in Article, Recipe ...) | name, thumbnailUrl, uploadDate | contentUrl or embedUrl, description, duration | regionsAllowed and ineligibleRegion together, past expires, Clip name/startOffset/url and unique offsets, SeekToAction target and input, live BroadcastEvent isLiveBroadcast and startDate, contentUrl is not the page URL |

Which items are checked: every top-level item (each JSON-LD object, `@graph` member, Microdata item and RDFa item),
plus items reached through `mainEntity`, `breadcrumb`, `video`, `hasPart`, `subjectOf` and `ItemList` carousels.
The schema.org and value checks run on every nested item.

## Rule reference

Rules are grouped by prefix: `syntax`, `schema`, `value`, `graph`, `google`, a prefix per feature, and `content`.

| Rule | Default | Description |
| --- | --- | --- |
| `syntax/json-invalid` | error | A JSON-LD script is not valid JSON. |
| `syntax/json-ld-shape` | error | A JSON-LD script holds something other than an object or an array of objects. |
| `syntax/empty-script` | warning | A JSON-LD script is empty. |
| `syntax/missing-context` | warning | A JSON-LD object has no @context, so its terms are not schema.org terms. |
| `syntax/unknown-context` | warning | The @context is not schema.org. |
| `syntax/unknown-keyword` | warning | A key starts with @ but is not a JSON-LD keyword. |
| `syntax/microdata-no-type` | warning | An itemscope element has no itemtype. |
| `syntax/rdfa-no-vocab` | warning | An RDFa typeof is used without a schema.org vocab or prefix. |
| `syntax/fetch-failed` | error | The page could not be fetched or read. |
| `schema/unknown-type` | error | The @type is not a schema.org type (often a typo or wrong case). |
| `schema/external-type` | info | The type comes from another vocabulary and is not checked. |
| `schema/missing-type` | info | An object has no @type (reported as a warning for top-level items). |
| `schema/unknown-property` | warning | The property is not a schema.org property (often a typo or wrong case). |
| `schema/unexpected-property` | info | The property exists but is not defined for this type. |
| `schema/superseded-property` | info | The property is superseded in schema.org. |
| `schema/invalid-enum` | error | The value is not a member of the expected schema.org enumeration. |
| `value/empty` | warning | A property has an empty value. |
| `value/date` | error | A date or date-time is not valid ISO 8601. |
| `value/duration` | error | A duration is not a valid ISO 8601 duration (PT1H30M). |
| `value/timezone` | info | A date-time has no timezone offset. |
| `value/url-relative` | warning | A URL is relative; use an absolute URL. |
| `value/url-invalid` | error | A URL property does not hold a URL. |
| `value/price` | error | A price is not a plain number (no currency symbols, thousands separators or ranges). |
| `value/currency` | error | A currency is not a three-letter ISO 4217 code. |
| `value/country` | warning | A country is not a two-letter ISO 3166-1 code. |
| `value/number` | error | A numeric property does not hold a number. |
| `value/boolean` | warning | A boolean property does not hold true or false. |
| `graph/unresolved-id` | warning | A node reference (@id) points to a node that is not defined on the page. |
| `graph/duplicate-id` | warning | The same @id is defined more than once with different types. |
| `google/required` | error | A property required for the rich result is missing. |
| `google/recommended` | warning | A recommended property is missing. |
| `google/deprecated-feature` | warning | Google no longer shows this rich result. |
| `article/author` | warning | Article author should be a Person or Organization with only the name in author.name. |
| `article/image` | warning | Article image should be a crawlable absolute URL or an ImageObject with a URL. |
| `product/offer-review-or-rating` | error | A Product needs at least one of offers, review or aggregateRating. |
| `product/price-zero` | info | A price of 0 means free; merchant listings need a price greater than zero. |
| `product/aggregate-offer` | error | An AggregateOffer needs lowPrice and priceCurrency. |
| `product/price-valid-until` | warning | priceValidUntil is in the past, which can stop the snippet from showing. |
| `merchant/required` | warning | A property needed for merchant listing experiences is missing. |
| `review/rating-range` | error | A rating value is outside the bestRating and worstRating range. |
| `review/author-name` | warning | A review author name looks like a promotion or is too long. |
| `review/item-type` | warning | The reviewed item type is not one Google supports for review snippets. |
| `review/self-serving` | warning | Reviews of a LocalBusiness or Organization on its own site are not eligible. |
| `breadcrumb/items` | error | A BreadcrumbList needs at least two ListItems. |
| `breadcrumb/position` | error | ListItem positions must be integers that start at 1 and do not repeat. |
| `breadcrumb/item` | error | Every ListItem except the last needs an item URL. |
| `event/status` | error | eventStatus is not one of the values Google supports. |
| `event/dates` | error | Event dates are inconsistent. |
| `event/online-only` | warning | Online-only events are not eligible for event rich results. |
| `job/employment-type` | error | employmentType is not one of FULL_TIME, PART_TIME, CONTRACTOR, ... |
| `job/salary` | error | baseSalary is not a MonetaryAmount with a currency and a valid unitText. |
| `job/remote` | error | Remote job markup is inconsistent. |
| `job/title` | warning | The job title contains codes, prices, dates or special characters. |
| `job/description` | error | The job description is missing, too short or the same as the title. |
| `job/expired` | warning | validThrough is in the past; the job is treated as expired. |
| `job/location-country` | error | jobLocation.address needs addressCountry. |
| `recipe/times` | warning | cookTime should come with prepTime, or use totalTime. |
| `recipe/yield` | warning | recipeYield is required when nutrition.calories is set. |
| `recipe/instructions` | warning | recipeInstructions should be HowToStep items with text. |
| `video/clips` | error | Clip markup is incomplete or has duplicate start offsets. |
| `video/regions` | warning | Use either regionsAllowed or ineligibleRegion, not both. |
| `video/expired` | warning | The video's expires date is in the past. |
| `video/live` | error | A live BroadcastEvent needs isLiveBroadcast and startDate. |
| `local/geo` | warning | Latitude and longitude should have at least five decimal places. |
| `local/opening-hours` | error | openingHoursSpecification has an invalid day or time. |
| `local/telephone` | warning | The telephone number should include the country code (+880...). |
| `local/price-range` | warning | priceRange should be shorter than 100 characters. |
| `org/logo` | warning | The logo should be at least 112x112 pixels and have a URL. |
| `org/identifier` | info | An Organization identifier is deprecated or malformed. |
| `faq/structure` | warning | An FAQPage question is missing its name or accepted answer text. |
| `content/not-visible` | info | Marked-up text does not appear in the visible page text. |
| `content/price-mismatch` | info | The marked-up price does not appear in the visible page text. |
| `content/no-structured-data` | info | No structured data was found. |

Severities: **error** means the item is not eligible for the rich result or the markup is broken; **warning** means
it should be fixed (missing recommended properties, likely mistakes); **info** is a hint.

## Configuration

Settings are read from the nearest `.rich-results-lint.toml`, or the `[tool.rich-results-lint]` table of the nearest
`pyproject.toml`, in the current directory or a parent. Command line options win; `--ignore` adds to the configured
list.

```toml
[tool.rich-results-lint]
fail-on = "error"            # error, warning, info or never
format = "text"              # text, json or sarif
select = []                  # empty means all rules
ignore = ["content/no-structured-data", "google/recommended"]
features = []                # e.g. ["product", "breadcrumb"]
content-checks = true
base-url = "https://shop.example/"
timeout = 20
user-agent = "my-ci-bot/1.0"

[tool.rich-results-lint.severity]
"merchant/required" = "error"   # shops that want merchant listings
"schema/unexpected-property" = "warning"
```

Unknown keys are an error, so typos in the config do not go unnoticed.

## Output formats and exit codes

- **text** - one line per finding: `file:line: severity rule: message [Type]`, then a summary.
- **json** - `{"tool", "version", "summary": {...}, "documents": [{"source", "url", "items": [...], "findings": [...]}]}`.
  Each finding has `rule`, `severity`, `message`, `source`, `line`, `path`, `type`, `feature` and `help`.
- **sarif** - SARIF 2.1.0 with one rule per rule id used, physical locations (file and line) and logical locations
  (JSON path). Upload it with `github/codeql-action/upload-sarif` to see findings in pull requests; see
  [`examples/github-code-scanning.yml`](examples/github-code-scanning.yml).

| Exit status | Meaning |
| --- | --- |
| 0 | No finding at or above `--fail-on`. |
| 1 | At least one finding at or above `--fail-on`. |
| 2 | Usage or configuration error, or a source could not be read or fetched (reported as `syntax/fetch-failed`). |

## Python API

```python
from rich_results_lint import Options, Severity, lint_file, lint_html, lint_jsonld, fetch

doc = lint_file("public/product.html", options=Options(ignore=["content"]))
for f in doc.findings:
    print(f.line, f.severity.value, f.rule, f.message)

doc = lint_html(html_string, source="preview", url="https://shop.example/p/1",
                options=Options(features=["product"], severity={"merchant/*": "error"}))
errors = [f for f in doc.findings if f.severity is Severity.ERROR]

page = fetch("https://shop.example/p/1")          # httpx, redirects followed
doc = lint_html(page.text, source=page.url, url=page.final_url)
```

`Document.items` holds the extracted `Item`s (types, properties, syntax, line, JSON path), so the extractor can also
be used on its own. `Options.now` sets the clock for expiry checks, which keeps tests stable.

## Examples

| File | Shows |
| --- | --- |
| [`examples/product-page.html`](examples/product-page.html) | A product page with typical mistakes |
| [`examples/article-ok.html`](examples/article-ok.html) | A clean NewsArticle |
| [`examples/microdata-recipe.html`](examples/microdata-recipe.html) | Microdata with a bad duration and a step label |
| [`examples/rich-results-lint.toml`](examples/rich-results-lint.toml) | A config file |
| [`examples/github-code-scanning.yml`](examples/github-code-scanning.yml) | CI with SARIF upload |
| [`examples/api_usage.py`](examples/api_usage.py) | The Python API |

## Testing

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
pytest            # about 310 tests
ruff check . && ruff format --check .
```

The suite runs every fixture in [`tests/fixtures/`](tests/fixtures/): `valid/` pages for each feature in JSON-LD,
Microdata and RDFa must produce nothing above the declared severity, and each `invalid/` page declares the rules it
must trigger in a leading `<!-- expect: ... -->` comment. Unit tests cover the JSON position parser, the three
extractors, value parsers, the vocabulary, every feature, content hints, the three output formats, config files, HTTP
fetching (with `httpx.MockTransport`, no network) and the CLI exit codes. CI runs on Python 3.10 to 3.13 and builds
the Docker image.

## Limitations

- **Not the Rich Results Test.** Google's own test renders JavaScript, applies unpublished rules and decides
  eligibility; this tool checks the documented requirements on the HTML it is given. A clean run does not guarantee a
  rich result, and Google may show none for policy or quality reasons.
- **No JavaScript.** Markup injected by scripts is not seen. Lint the rendered HTML (for example from your static site
  build, or saved from a headless browser) if your structured data is added client side.
- **Subset of features.** Only the features listed above are checked in depth. Others (Course, Dataset, Movie, Software
  app, Vacation rental, Profile page, Q&A, Discussion forum, Paywalled content, Speakable, Math solvers, Education Q&A,
  Image metadata, Employer rating, Carousel details) get the schema.org and value checks only.
- **Merchant listing depth.** Shipping (`OfferShippingDetails`), return policies (`MerchantReturnPolicy`), member
  pricing, product variants (`ProductGroup`), certifications and size specifications are not validated yet.
- **Recommended lists are selective for Organization.** Google recommends many Organization properties; the linter
  reports the ones that matter most (name, url, logo, sameAs, address, a contact) to keep the noise down.
- **Content hints are heuristics.** Text rendered by JavaScript, abbreviations or different number formats can cause
  `content/*` hints on correct pages, and they are only computed for JSON-LD.
- **RDFa Lite only.** Full RDFa 1.1 (`rel`, `rev`, `about` chaining, `inlist`, CURIE edge cases) is not implemented.
  Microdata `itemref` is supported.
- **FAQ requirements.** Google removed the FAQ documentation, so FAQ structure is checked against schema.org only.
- **Vocabulary snapshot.** The bundled schema.org vocabulary is version 30.1. Newer terms are reported as unknown
  until the vocabulary is rebuilt with `scripts/build_vocab.py`.

## Data and licences

- schema.org vocabulary: <https://schema.org/version/latest/schemaorg-current-https.jsonld>, release 30.1
  (2026-09-16), trimmed by `scripts/build_vocab.py` to types, properties, domains, ranges, supersession and
  enumeration members. schema.org is licensed under
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/); the trimmed file
  `src/rich_results_lint/data/schemaorg.json` is under the same licence. See [NOTICE.md](NOTICE.md).
- Google requirements are summarised in the code and in this README from the public documentation; no Google text
  is bundled.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every new rule needs a fixture and a link to the documentation it comes from.

## License

[MIT](LICENSE) © 2026 Saizul Amin. The bundled schema.org vocabulary is CC BY-SA 3.0, see [NOTICE.md](NOTICE.md).
