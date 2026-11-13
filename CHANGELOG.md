# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
