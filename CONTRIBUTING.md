# Contributing

Thanks for helping improve rich-results-lint. Bug reports, new fixtures, rule fixes and pull requests are welcome.

## Getting started

```bash
git clone https://github.com/saizul/rich-results-lint.git
cd rich-results-lint
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
pytest
ruff check . && ruff format --check .
```

Python 3.10 or newer is required.

## Project layout

| Path | Purpose |
| --- | --- |
| `src/rich_results_lint/extract/` | HTML tree (`dom.py`), JSON with line numbers (`jsonpos.py`), JSON-LD, Microdata and RDFa extractors |
| `src/rich_results_lint/vocab.py` | Loader for the bundled schema.org vocabulary |
| `src/rich_results_lint/values.py` | Date, duration, URL, price, currency and country parsers |
| `src/rich_results_lint/checks/schema.py` | schema.org, value and `@id` graph checks for every item |
| `src/rich_results_lint/checks/features/` | One module per Google rich result feature |
| `src/rich_results_lint/checks/content.py` | Visible-content hints |
| `src/rich_results_lint/rules.py` | Rule registry (id, default severity, description) |
| `src/rich_results_lint/linter.py` | Orchestration, options, filtering |
| `src/rich_results_lint/report/` | Text, JSON and SARIF output |
| `src/rich_results_lint/cli.py` | Command line interface |
| `scripts/build_vocab.py` | Rebuilds `data/schemaorg.json` from a schema.org release |
| `tests/fixtures/valid`, `tests/fixtures/invalid` | Pages checked by `tests/test_fixtures.py` |

## Adding or changing a rule

1. **Cite the source.** Google rules must come from a page under
   <https://developers.google.com/search/docs/appearance/structured-data/>. Put the link and the date you checked it
   in the pull request. If the documentation is unclear, make the rule a warning and say so in the README limitations.
2. **Register it** in `rules.py` with a default severity: `error` only when Google says the item is not eligible.
3. **Add a fixture.** Put a page in `tests/fixtures/invalid/` with `<!-- expect: your/rule -->` at the top, and make
   sure the `valid/` fixtures stay clean. Add focused unit tests for edge cases.
4. **Update the README** feature table and rule reference, and `CHANGELOG.md` under `[Unreleased]`.

## Updating the schema.org vocabulary

```bash
curl -sSLo /tmp/schemaorg.jsonld https://schema.org/version/latest/schemaorg-current-https.jsonld
python scripts/build_vocab.py /tmp/schemaorg.jsonld <version>
pytest
```

Record the new version in `NOTICE.md` and `CHANGELOG.md`.

## Guidelines

- No network access in tests: use `httpx.MockTransport`.
- Keep runtime dependencies minimal (`httpx` only, plus `tomli` on Python 3.10).
- Messages say what is wrong and how to fix it, in one sentence where possible.
- `ruff check` and `ruff format --check` must pass.

## Commit messages

Short imperative subject line (`Add Course rules`, `Fix RDFa prefix handling`), with details in the body when needed.

## Releasing

1. Update `src/rich_results_lint/_version.py` and move the `[Unreleased]` entries in `CHANGELOG.md`.
2. Tag `vX.Y.Z` and publish a GitHub release. The `Publish container image` workflow pushes
   `ghcr.io/saizul/rich-results-lint:X.Y.Z`.

## Code of conduct

Be respectful and constructive. Harassment of any kind is not tolerated.
