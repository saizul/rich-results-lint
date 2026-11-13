"""Use rich-results-lint from Python.

Run from the repository root:  python examples/api_usage.py
"""

from __future__ import annotations

from pathlib import Path

from rich_results_lint import Options, Severity, lint_file, lint_html

HERE = Path(__file__).parent

# Lint a file and print errors only.
doc = lint_file(HERE / "product-page.html", options=Options(ignore=["content"]))
for finding in doc.findings:
    if finding.severity is Severity.ERROR:
        print(f"{finding.line}: {finding.rule}: {finding.message}")

# Lint HTML from memory, for example in a CMS preview or a test suite.
html = """<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Event", "name": "Book fair", "startDate": "2030-02-01",
 "location": {"@type": "Place", "name": "Bangla Academy",
              "address": {"@type": "PostalAddress", "addressLocality": "Dhaka", "addressCountry": "BD"}}}
</script>"""
result = lint_html(html, source="event-preview", options=Options(features=["event"], content_checks=False))
print(f"{len(result.items)} item(s), {len(result.findings)} finding(s)")
for finding in result.findings:
    print(f"  {finding.severity.value}: {finding.rule}: {finding.message}")
