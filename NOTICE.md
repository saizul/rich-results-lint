# Third-party data

The code of rich-results-lint is MIT licensed (see [LICENSE](LICENSE)). It bundles one third-party data file.

## schema.org vocabulary

- File: `src/rich_results_lint/data/schemaorg.json`
- Source: <https://schema.org/version/latest/schemaorg-current-https.jsonld>, schema.org release 30.1 (2026-09-16),
  retrieved 2026-11-13.
- Changes: trimmed by `scripts/build_vocab.py` to type names and parent types, property names with their domain and
  range types and `supersededBy`, data types, and enumeration members. Labels, comments, external mappings and the
  country-specific nonprofit status enumerations were
  removed.
- Licence: schema.org is licensed under the
  [Creative Commons Attribution-ShareAlike 3.0 Unported licence](https://creativecommons.org/licenses/by-sa/3.0/)
  (see <https://schema.org/docs/terms.html>). The trimmed file is a derivative of schema.org and is distributed under
  the same licence.

## Google Search documentation

The rules about Google rich results are written for this project from the public Google Search Central documentation
(<https://developers.google.com/search/docs/appearance/structured-data/>, checked 2026-11-13). No Google text or
code is bundled. Google and Google Search are trademarks of Google LLC; this project is not affiliated with or
endorsed by Google.
