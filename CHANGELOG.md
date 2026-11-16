# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Software app feature (`software-app`) for SoftwareApplication, MobileApplication, WebApplication and co-typed
  VideoGame: required name, offers with a price, a rating or review, priceCurrency for paid apps, and Google's
  `applicationCategory` values with suggestions. New rules `software/rating`, `software/category` and
  `software/video-game`.
- Dataset feature (`dataset`): description length (50 to 5000 characters), DataDownload distributions with
  `contentUrl`, ISO 8601 `temporalCoverage` dates and intervals including open ends, creator type and DataCatalog
  name. New rules `dataset/description`, `dataset/distribution`, `dataset/temporal-coverage`, `dataset/creator` and
  `dataset/license`.
- Profile page feature (`profile-page`): one Person or Organization as `mainEntity`, interaction statistics and date
  order. New rules `profile/main-entity`, `profile/interaction` and `profile/dates`.
- Discussion forum feature (`discussion-forum`) for DiscussionForumPosting and nested Comment replies: author, date
  and content requirements, future dates and replies dated before their post. New rules `forum/author` and
  `forum/dates`.

### Changed

- DiscussionForumPosting is no longer checked against the Article feature; it is covered by `discussion-forum`.
- `--list-features` sizes its columns to the longest feature id and name.

## [0.1.0] - 2026-11-13

### Added

- Extraction of JSON-LD (with line numbers for every property, `@graph`, arrays, `@id` references, `@list`, value
  objects, prefixed and full IRI terms, HTML comment wrappers), Microdata (including `itemid` and `itemref`) and RDFa
  Lite (`vocab`, `typeof`, `property`, `prefix`, `resource`).
- Bundled, trimmed schema.org 30.1 vocabulary and `scripts/build_vocab.py` to rebuild it.
- schema.org checks: unknown and external types, unknown, unexpected and superseded properties with suggestions,
  missing `@type`, enumeration values.
- Value checks: ISO 8601 dates, date-times, timezones and durations; relative and invalid URLs; prices; ISO 4217
  currencies; ISO 3166-1 countries; numbers; booleans; empty values.
- Graph checks: unresolved `@id` references and conflicting duplicate `@id`s, with reference resolution across
  scripts.
- Google rich result checks (verified 2026-11-13) for Article, Product snippet, merchant listing, Review snippet,
  Breadcrumb, FAQ (deprecated), How-to (removed), Local business, Organization, Event, Job posting, Recipe and Video.
- Content mismatch hints for names, headlines and prices that are not visible on the page.
- `rich-results-lint` command: files, directories, URLs (httpx) and standard input; text, JSON and SARIF 2.1.0
  output; `--select`, `--ignore`, `--severity`, `--feature`, `--fail-on`; exit codes 0, 1 and 2; configuration in
  `pyproject.toml` or `.rich-results-lint.toml`.
- Python API: `lint_html`, `lint_jsonld`, `lint_file`, `fetch`, `Options`.
- Dockerfile and a workflow that publishes a multi-arch image to `ghcr.io/saizul/rich-results-lint`.
- CI on Python 3.10 to 3.13, examples and test fixtures for every feature.

[Unreleased]: https://github.com/saizul/rich-results-lint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saizul/rich-results-lint/releases/tag/v0.1.0
