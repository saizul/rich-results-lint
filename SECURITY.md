# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report privately through
[GitHub Security Advisories](https://github.com/saizul/rich-results-lint/security/advisories/new). Include the
affected version, a description, steps to reproduce and the impact you expect. You should receive a reply within
7 days. Once a fix is released, the advisory is published with credit to the reporter unless you prefer otherwise.

## Scope

In scope: input files or HTTP responses that make the linter hang, use excessive memory or CPU, crash, write outside
the requested output file, or make requests to hosts other than the URLs it was given (it follows redirects only).

Out of scope: wrong or missing findings (please open a normal issue), and problems in Google Search itself.

## Recommendations for users

- When you lint URLs in CI, lint your own sites. The linter downloads at most 10 MB per page and follows up to 10
  redirects; run it in a container or a sandbox if you lint untrusted URLs.
- The SARIF and JSON reports contain snippets of your structured data. Treat them like build logs.
